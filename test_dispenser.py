"""Tests for Dispenser — denomination logic, inventory, dispensing workflow."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from hardware.dispenser import (
    Dispenser, ChipDenomination, ChipColor,
    DispenseRequest, InsufficientInventoryError
)
from hardware.gpio_controller import GPIOController, PinConfig


@pytest.fixture
def gpio():
    ctrl = GPIOController([
        PinConfig(motor_pin=17, sensor_pin=27),
        PinConfig(motor_pin=22, sensor_pin=23),
        PinConfig(motor_pin=24, sensor_pin=25),
        PinConfig(motor_pin=5, sensor_pin=6),
    ])
    ctrl.setup()
    return ctrl


@pytest.fixture
def denominations():
    return [
        ChipDenomination(color=ChipColor.WHITE, value=1,   slot=0, inventory=100),
        ChipDenomination(color=ChipColor.RED,   value=5,   slot=1, inventory=50),
        ChipDenomination(color=ChipColor.GREEN, value=25,  slot=2, inventory=20),
        ChipDenomination(color=ChipColor.BLACK, value=100, slot=3, inventory=10),
    ]


@pytest.fixture
def dispenser(gpio, denominations):
    return Dispenser(gpio, denominations)


# ── Inventory ──────────────────────────────────────────────────────────────────

def test_get_inventory(dispenser):
    inv = dispenser.get_inventory()
    assert inv["white"] == 100
    assert inv["black"] == 10


def test_set_inventory(dispenser):
    dispenser.set_inventory(ChipColor.WHITE, 50)
    assert dispenser.get_inventory()["white"] == 50


def test_total_value(dispenser):
    # 100*1 + 50*5 + 20*25 + 10*100 = 100 + 250 + 500 + 1000 = 1850 * 100 cents
    assert dispenser.total_value_available() == 185000


# ── Chip calculation ───────────────────────────────────────────────────────────

def test_calculate_chips_exact(dispenser):
    chips = dispenser.calculate_chips(10000)  # $100
    assert chips[ChipColor.BLACK] == 1


def test_calculate_chips_greedy(dispenser):
    chips = dispenser.calculate_chips(3100)  # $31
    assert chips[ChipColor.GREEN] == 1   # $25
    assert chips[ChipColor.RED] == 1     # $5
    assert chips[ChipColor.WHITE] == 1   # $1


def test_calculate_chips_insufficient_raises(dispenser):
    with pytest.raises(InsufficientInventoryError):
        dispenser.calculate_chips(99999999)


def test_calculate_chips_respects_inventory(dispenser):
    dispenser.set_inventory(ChipColor.BLACK, 0)
    dispenser.set_inventory(ChipColor.GREEN, 0)
    dispenser.set_inventory(ChipColor.RED, 0)
    dispenser.set_inventory(ChipColor.WHITE, 5)
    chips = dispenser.calculate_chips(300)  # $3
    assert chips[ChipColor.WHITE] == 3


# ── Dispensing ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dispense_success(dispenser):
    with patch.object(dispenser, "_dispense_slot", new_callable=AsyncMock) as mock_slot:
        req = DispenseRequest(amount_cents=500, payment_ref="txn_123")  # $5
        result = await dispenser.dispense(req)

    assert result.success is True
    assert result.dispensed.get("red") == 1
    assert result.total_value == 500


@pytest.mark.asyncio
async def test_dispense_updates_inventory(dispenser):
    with patch.object(dispenser, "_dispense_slot", new_callable=AsyncMock):
        req = DispenseRequest(amount_cents=500)
        await dispenser.dispense(req)

    assert dispenser.get_inventory()["red"] == 49  # was 50


@pytest.mark.asyncio
async def test_dispense_insufficient_returns_failure(dispenser):
    req = DispenseRequest(amount_cents=99999999)
    result = await dispenser.dispense(req)
    assert result.success is False
    assert "insufficient" in result.error.lower()


@pytest.mark.asyncio
async def test_dispense_hardware_error_triggers_estop(dispenser):
    with patch.object(dispenser, "_dispense_slot", side_effect=RuntimeError("Motor jam")):
        with patch.object(dispenser.gpio, "all_motors_off") as mock_stop:
            req = DispenseRequest(amount_cents=100)
            result = await dispenser.dispense(req)

    assert result.success is False
    mock_stop.assert_called_once()


# ── Status ─────────────────────────────────────────────────────────────────────

def test_status_structure(dispenser):
    status = dispenser.status()
    assert "slots" in status
    assert "total_value_cents" in status
    assert status["hardware_mode"] == "mock"
    assert len(status["slots"]) == 4
