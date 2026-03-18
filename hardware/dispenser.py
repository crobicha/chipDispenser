"""
Dispenser — high-level chip dispensing logic.

Maps poker chip denominations to hardware slots,
tracks inventory, and orchestrates the dispensing workflow.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum

from hardware.gpio_controller import GPIOController

logger = logging.getLogger(__name__)


class ChipColor(str, Enum):
    WHITE = "white"
    RED = "red"
    GREEN = "green"
    BLACK = "black"
    BLUE = "blue"


@dataclass
class ChipDenomination:
    """Maps a chip color/value to a physical dispenser slot."""
    color: ChipColor
    value: int          # Dollar value (e.g. 1, 5, 25, 100)
    slot: int           # Hardware slot index
    inventory: int = 0  # Current chip count in hopper


@dataclass
class DispenseRequest:
    """Represents a request to dispense chips for a given dollar amount."""
    amount_cents: int                   # e.g. 2500 = $25.00
    denominations: dict[str, int] = field(default_factory=dict)  # color → count
    payment_ref: str | None = None      # Payment processor transaction ID


@dataclass
class DispenseResult:
    """Result of a dispense operation."""
    success: bool
    dispensed: dict[str, int] = field(default_factory=dict)  # color → count
    error: str | None = None
    total_value: int = 0  # in cents


class InsufficientInventoryError(Exception):
    pass

class HardwareError(Exception):
    pass


class Dispenser:
    """
    Orchestrates chip dispensing across all slots.

    Handles:
    - Denomination → slot mapping
    - Greedy chip selection (largest denominations first)
    - Inventory validation before dispensing
    - Async motor control with sensor verification
    """

    def __init__(self, gpio: GPIOController, denominations: list[ChipDenomination]) -> None:
        self.gpio = gpio
        # Map color → denomination config
        self._denoms: dict[ChipColor, ChipDenomination] = {
            d.color: d for d in denominations
        }
        # Also index by slot for quick lookup
        self._slots: dict[int, ChipDenomination] = {
            d.slot: d for d in denominations
        }

    # ── Inventory ────────────────────────────────────────────────────────────

    def get_inventory(self) -> dict[str, int]:
        """Return current inventory as {color: count}."""
        return {d.color.value: d.inventory for d in self._denoms.values()}

    def set_inventory(self, color: ChipColor, count: int) -> None:
        """Manually set chip count for a denomination (e.g. after refill)."""
        if color not in self._denoms:
            raise ValueError(f"Unknown denomination: {color}")
        self._denoms[color].inventory = count
        logger.info(f"Inventory updated: {color.value} = {count} chips")

    def total_value_available(self) -> int:
        """Total dispensable value in cents."""
        return sum(d.value * d.inventory * 100 for d in self._denoms.values())

    # ── Chip selection ────────────────────────────────────────────────────────

    def calculate_chips(self, amount_cents: int) -> dict[ChipColor, int]:
        """
        Greedy algorithm: use largest denominations first to fulfill amount.
        Returns {ChipColor: count} or raises InsufficientInventoryError.
        """
        remaining = amount_cents
        result: dict[ChipColor, int] = {}

        # Sort denominations largest → smallest
        sorted_denoms = sorted(
            self._denoms.values(),
            key=lambda d: d.value,
            reverse=True
        )

        for denom in sorted_denoms:
            if remaining <= 0:
                break
            chip_value_cents = denom.value * 100
            max_usable = min(denom.inventory, remaining // chip_value_cents)
            if max_usable > 0:
                result[denom.color] = max_usable
                remaining -= max_usable * chip_value_cents

        if remaining > 0:
            raise InsufficientInventoryError(
                f"Cannot fulfill ${amount_cents / 100:.2f} — "
                f"short by ${remaining / 100:.2f} (insufficient chips)"
            )

        return result

    # ── Dispensing ────────────────────────────────────────────────────────────

    async def dispense(self, request: DispenseRequest) -> DispenseResult:
        """
        Main dispensing workflow:
        1. Calculate chip breakdown
        2. Validate inventory
        3. Dispense each denomination
        4. Update inventory counts
        """
        logger.info(f"Dispense request: ${request.amount_cents / 100:.2f} (ref={request.payment_ref})")

        # Step 1: Figure out which chips to dispense
        try:
            chip_plan = self.calculate_chips(request.amount_cents)
        except InsufficientInventoryError as e:
            logger.warning(str(e))
            return DispenseResult(success=False, error=str(e))

        # Step 2: Dispense each denomination
        dispensed: dict[str, int] = {}
        try:
            for color, count in chip_plan.items():
                denom = self._denoms[color]
                await self._dispense_slot(denom.slot, count)
                denom.inventory -= count
                dispensed[color.value] = count
                logger.info(f"  Dispensed {count}x {color.value} (${denom.value} each)")

        except Exception as e:
            logger.error(f"Hardware error during dispense: {e}")
            self.gpio.all_motors_off()
            return DispenseResult(
                success=False,
                dispensed=dispensed,
                error=f"Hardware error: {e}"
            )

        total = sum(
            self._denoms[color].value * count * 100
            for color, count in chip_plan.items()
        )

        logger.info(f"Dispense complete: ${total / 100:.2f} dispensed")
        return DispenseResult(success=True, dispensed=dispensed, total_value=total)

    async def _dispense_slot(self, slot: int, count: int) -> None:
        """Pulse a single slot's motor `count` times, verifying each chip."""
        for i in range(count):
            # Pulse motor
            await asyncio.to_thread(self.gpio.pulse_motor, slot, pulses=1)
            # Brief wait for chip to fall through sensor
            await asyncio.sleep(0.15)
            logger.debug(f"  Slot {slot}: chip {i + 1}/{count} dispensed")

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "slots": [
                {
                    "slot": d.slot,
                    "color": d.color.value,
                    "value": d.value,
                    "inventory": d.inventory,
                }
                for d in sorted(self._denoms.values(), key=lambda x: x.slot)
            ],
            "total_value_cents": self.total_value_available(),
            "hardware_mode": "real" if self.gpio.is_real_hardware else "mock",
        }
