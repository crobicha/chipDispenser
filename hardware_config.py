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
    PinConfig(motor_pin=17, sensor_pin=27),   # Slot 0 — White  $1
    PinConfig(motor_pin=22, sensor_pin=23),   # Slot 1 — Red    $5
    PinConfig(motor_pin=24, sensor_pin=25),   # Slot 2 — Green  $25
    PinConfig(motor_pin=5,  sensor_pin=6),    # Slot 3 — Black  $100
]

# ── Default chip denominations ─────────────────────────────────────────────────

DEFAULT_DENOMINATIONS: list[ChipDenomination] = [
    ChipDenomination(color=ChipColor.WHITE, value=1,   slot=0, inventory=100),
    ChipDenomination(color=ChipColor.RED,   value=5,   slot=1, inventory=100),
    ChipDenomination(color=ChipColor.GREEN, value=25,  slot=2, inventory=50),
    ChipDenomination(color=ChipColor.BLACK, value=100, slot=3, inventory=20),
]
