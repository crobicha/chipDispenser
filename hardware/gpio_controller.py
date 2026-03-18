"""
GPIO Controller — low-level pin management for the chip dispenser.

Automatically uses real RPi.GPIO on a Raspberry Pi,
or falls back to MockGPIO in dev/test environments.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Auto-detect hardware environment
try:
    import RPi.GPIO as GPIO  # type: ignore
    IS_REAL_PI = True
    logger.info("Running on real Raspberry Pi — using RPi.GPIO")
except (ImportError, RuntimeError):
    from hardware.mock_gpio import (  # type: ignore
        BCM, OUT, IN, HIGH, LOW, RISING, FALLING, PUD_UP,
        setmode, setwarnings, setup, output, input as gpio_input,
        cleanup, add_event_detect, remove_event_detect,
        _simulate_pin_high, _simulate_pin_low, _get_pin_state
    )
    import hardware.mock_gpio as GPIO
    IS_REAL_PI = False
    logger.warning("RPi.GPIO not found — using MockGPIO (dev/test mode)")


@dataclass
class PinConfig:
    """Pin assignments for one dispenser slot."""
    motor_pin: int          # Controls motor to spin dispenser
    sensor_pin: int         # IR or optical sensor — detects chip passing
    enable_pin: int | None = None  # Optional motor enable/PWM pin


class GPIOController:
    """
    Manages raw GPIO operations: motor pulses, sensor reads, cleanup.

    Usage:
        controller = GPIOController(pin_configs)
        controller.setup()
        controller.pulse_motor(slot=0, pulses=3)
        controller.teardown()
    """

    def __init__(self, pin_configs: list[PinConfig]) -> None:
        self.pin_configs = pin_configs
        self._initialized = False

    def setup(self) -> None:
        """Initialize GPIO pins for all slots."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for slot, cfg in enumerate(self.pin_configs):
            GPIO.setup(cfg.motor_pin, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(cfg.sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            if cfg.enable_pin is not None:
                GPIO.setup(cfg.enable_pin, GPIO.OUT, initial=GPIO.LOW)
            logger.debug(f"Slot {slot} pins initialized: motor={cfg.motor_pin}, sensor={cfg.sensor_pin}")

        self._initialized = True
        logger.info(f"GPIOController initialized with {len(self.pin_configs)} slot(s)")

    def pulse_motor(self, slot: int, pulses: int, pulse_ms: int = 100, gap_ms: int = 50) -> None:
        """
        Pulse the motor for a given slot N times.

        Each pulse = motor ON for pulse_ms, then OFF for gap_ms.
        One pulse typically dispenses one chip (calibrate per hardware).
        """
        if not self._initialized:
            raise RuntimeError("GPIOController.setup() must be called before use")

        cfg = self.pin_configs[slot]
        logger.info(f"Slot {slot}: pulsing motor {pulses}x (pin {cfg.motor_pin})")

        for i in range(pulses):
            GPIO.output(cfg.motor_pin, GPIO.HIGH)
            time.sleep(pulse_ms / 1000)
            GPIO.output(cfg.motor_pin, GPIO.LOW)
            time.sleep(gap_ms / 1000)
            logger.debug(f"  Pulse {i + 1}/{pulses} complete")

    def read_sensor(self, slot: int) -> bool:
        """
        Read the optical/IR sensor for a slot.
        Returns True if chip is detected (sensor blocked).
        """
        if not self._initialized:
            raise RuntimeError("GPIOController.setup() must be called before use")

        cfg = self.pin_configs[slot]
        # Active LOW — sensor pulls pin LOW when chip is present
        raw = GPIO.input(cfg.sensor_pin)
        detected = raw == GPIO.LOW
        logger.debug(f"Slot {slot} sensor (pin {cfg.sensor_pin}): {'CHIP DETECTED' if detected else 'clear'}")
        return detected

    def set_motor(self, slot: int, state: bool) -> None:
        """Directly set motor ON or OFF (for manual control / emergency stop)."""
        if not self._initialized:
            raise RuntimeError("GPIOController.setup() must be called before use")

        cfg = self.pin_configs[slot]
        GPIO.output(cfg.motor_pin, GPIO.HIGH if state else GPIO.LOW)
        logger.debug(f"Slot {slot} motor set {'ON' if state else 'OFF'}")

    def all_motors_off(self) -> None:
        """Emergency stop — turn off all motors immediately."""
        for slot, cfg in enumerate(self.pin_configs):
            GPIO.output(cfg.motor_pin, GPIO.LOW)
            if cfg.enable_pin is not None:
                GPIO.output(cfg.enable_pin, GPIO.LOW)
        logger.warning("All motors stopped (emergency stop)")

    def teardown(self) -> None:
        """Release all GPIO resources."""
        self.all_motors_off()
        GPIO.cleanup()
        self._initialized = False
        logger.info("GPIOController teardown complete")

    @property
    def slot_count(self) -> int:
        return len(self.pin_configs)

    @property
    def is_real_hardware(self) -> bool:
        return IS_REAL_PI
