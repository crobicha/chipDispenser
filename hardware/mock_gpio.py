"""
Mock GPIO module for development and testing without physical Raspberry Pi hardware.
Drop-in replacement for RPi.GPIO — automatically used when not running on a Pi.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# GPIO numbering modes
BCM = "BCM"
BOARD = "BOARD"

# Pin directions
IN = "IN"
OUT = "OUT"

# Pin states
HIGH = 1
LOW = 0

# Edge detection
RISING = "RISING"
FALLING = "FALLING"
BOTH = "BOTH"

# Pull up/down
PUD_UP = "PUD_UP"
PUD_DOWN = "PUD_DOWN"
PUD_OFF = "PUD_OFF"

_pin_states: dict[int, int] = {}
_mode: str | None = None


def setmode(mode: str) -> None:
    global _mode
    _mode = mode
    logger.debug(f"[MockGPIO] Mode set to {mode}")


def setwarnings(flag: bool) -> None:
    logger.debug(f"[MockGPIO] Warnings set to {flag}")


def setup(pin: int, direction: str, pull_up_down: str = PUD_OFF, initial: int = LOW) -> None:
    _pin_states[pin] = initial
    logger.debug(f"[MockGPIO] Pin {pin} set up as {direction}, initial={initial}")


def output(pin: int, state: int) -> None:
    _pin_states[pin] = state
    logger.debug(f"[MockGPIO] Pin {pin} → {'HIGH' if state else 'LOW'}")


def input(pin: int) -> int:
    state = _pin_states.get(pin, LOW)
    logger.debug(f"[MockGPIO] Pin {pin} read → {state}")
    return state


def cleanup(pins: list[int] | None = None) -> None:
    if pins:
        for pin in pins:
            _pin_states.pop(pin, None)
    else:
        _pin_states.clear()
    logger.debug(f"[MockGPIO] Cleanup called on {'all pins' if not pins else pins}")


def add_event_detect(pin: int, edge: str, callback=None, bouncetime: int = 200) -> None:
    logger.debug(f"[MockGPIO] Event detect added on pin {pin}, edge={edge}")


def remove_event_detect(pin: int) -> None:
    logger.debug(f"[MockGPIO] Event detect removed from pin {pin}")


# Test helpers — not part of real GPIO API
def _simulate_pin_high(pin: int) -> None:
    """Simulate a pin going HIGH (for unit tests)."""
    _pin_states[pin] = HIGH

def _simulate_pin_low(pin: int) -> None:
    """Simulate a pin going LOW (for unit tests)."""
    _pin_states[pin] = LOW

def _get_pin_state(pin: int) -> int:
    """Read simulated pin state directly (for unit tests)."""
    return _pin_states.get(pin, LOW)
