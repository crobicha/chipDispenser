"""
GPIO Controller — low-level pin management for the chip dispenser.

Motor control: Adafruit Stepper Motor HAT (I2C via adafruit_motorkit).
  - Motors addressed by HAT port number (1–4, corresponding to M1–M4).
  - Falls back to MockMotorKit in dev/test environments.

Sensor control: direct RPi.GPIO (IR/optical sensors on GPIO pins).
  - Falls back to MockGPIO in dev/test environments.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Motor HAT (MotorKit via I2C) ───────────────────────────────────────────────
# Confirmed via `i2cdetect -y 1` — HAT address jumpers shift it from 0x60 to 0x6f
MOTOR_HAT_ADDRESS: int = 0x6f

try:
    from adafruit_motorkit import MotorKit  # type: ignore
    _motor_kit = MotorKit(address=MOTOR_HAT_ADDRESS)
    IS_REAL_PI = True
    logger.info("Adafruit MotorKit found — using Motor HAT")
except (ImportError, RuntimeError, ValueError) as e:
    from hardware.mock_gpio import MockMotorKit  # type: ignore
    _motor_kit = MockMotorKit()
    IS_REAL_PI = False
    logger.warning(f"adafruit_motorkit not found — using MockMotorKit (dev/test mode). Reason: {type(e).__name__}: {e}")

# ── GPIO for sensors ───────────────────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO  # type: ignore
except (ImportError, RuntimeError, ValueError):
    from hardware.mock_gpio import (  # type: ignore
        BCM, OUT, IN, HIGH, LOW, RISING, FALLING, PUD_UP,
        setmode, setwarnings, setup, output, input as gpio_input,
        cleanup, add_event_detect, remove_event_detect,
        _simulate_pin_high, _simulate_pin_low, _get_pin_state
    )
    import hardware.mock_gpio as GPIO


@dataclass
class PinConfig:
    """Pin assignments for one dispenser slot."""
    motor_port: int         # Motor HAT port number (1–4 → M1–M4)
    sensor_pin: int         # IR or optical sensor GPIO pin — detects chip passing


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
        """Initialize GPIO sensor pins and ensure all motors are off."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for slot, cfg in enumerate(self.pin_configs):
            GPIO.setup(cfg.sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            # Ensure motor starts off
            _motor_kit.get_motor(cfg.motor_port).throttle = None
            logger.debug(f"Slot {slot} initialized: M{cfg.motor_port}, sensor pin {cfg.sensor_pin}")

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
        motor = _motor_kit.get_motor(cfg.motor_port)
        logger.info(f"Slot {slot}: pulsing M{cfg.motor_port} {pulses}x")

        for i in range(pulses):
            motor.throttle = 1.0
            time.sleep(pulse_ms / 1000)
            motor.throttle = None
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
        _motor_kit.get_motor(cfg.motor_port).throttle = 1.0 if state else None
        logger.debug(f"Slot {slot} M{cfg.motor_port} set {'ON' if state else 'OFF'}")

    def all_motors_off(self) -> None:
        """Emergency stop — release all motors immediately."""
        for cfg in self.pin_configs:
            _motor_kit.get_motor(cfg.motor_port).throttle = None
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
