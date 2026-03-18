"""
Hardware configuration — pin assignments and chip denominations.

Edit this file to match your physical wiring.
BCM (Broadcom) pin numbering is used throughout.
"""

from hardware.gpio_controller import PinConfig
from hardware.dispenser import ChipDenomination, ChipColor

# ── Pin assignments ────────────────────────────────────────────────────────────
# Slot 0 → White ($1), Slot 1 → Red ($5), Slot 2 → Green ($25), Slot 3 → Black ($100)

PIN_CONFIGS: list[PinConfig] = [
    PinConfig(motor_port=1, sensor_pin=27),   # Slot 0 — White  $1   (M1)

    PinConfig(motor_port=2, sensor_pin=23),   # Slot 1 — Red    $5   (M2)

    PinConfig(motor_port=3, sensor_pin=25),   # Slot 2 — Green  $25  (M3)

    PinConfig(motor_port=4, sensor_pin=6),    # Slot 3 — Black  $100 (M4)
]

# ── Default chip denominations ─────────────────────────────────────────────────

# TODO: defaults are useful for testing but should be set programatically
DEFAULT_DENOMINATIONS: list[ChipDenomination] = [
    ChipDenomination(color=ChipColor.WHITE, value=1,   slot=0, inventory=100),
    ChipDenomination(color=ChipColor.RED,   value=5,   slot=1, inventory=100),
    ChipDenomination(color=ChipColor.GREEN, value=25,  slot=2, inventory=50),
    ChipDenomination(color=ChipColor.BLACK, value=100, slot=3, inventory=20),
]
