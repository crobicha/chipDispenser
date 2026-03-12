"""Tests for GPIOController using MockGPIO."""

import pytest
from hardware.gpio_controller import GPIOController, PinConfig
import hardware.mock_gpio as mock_gpio


@pytest.fixture
def pin_configs():
    return [
        PinConfig(motor_pin=17, sensor_pin=27),
        PinConfig(motor_pin=22, sensor_pin=23),
    ]


@pytest.fixture
def controller(pin_configs):
    ctrl = GPIOController(pin_configs)
    ctrl.setup()
    yield ctrl
    ctrl.teardown()


def test_setup_initializes_pins(controller):
    assert controller._initialized is True


def test_slot_count(controller, pin_configs):
    assert controller.slot_count == len(pin_configs)


def test_is_not_real_hardware(controller):
    assert controller.is_real_hardware is False


def test_pulse_motor_toggles_pin(controller):
    """Motor pin should end LOW after a pulse cycle."""
    controller.pulse_motor(slot=0, pulses=1, pulse_ms=1, gap_ms=1)
    state = mock_gpio._get_pin_state(17)
    assert state == mock_gpio.LOW


def test_pulse_motor_multiple(controller):
    """Should complete without error for multiple pulses."""
    controller.pulse_motor(slot=0, pulses=5, pulse_ms=1, gap_ms=1)


def test_read_sensor_default_clear(controller):
    """Sensor should read clear (False) when pin is HIGH (not pulled LOW)."""
    mock_gpio._simulate_pin_high(27)
    assert controller.read_sensor(slot=0) is False


def test_read_sensor_detects_chip(controller):
    """Sensor reads True when pin is pulled LOW (chip present)."""
    mock_gpio._simulate_pin_low(27)
    assert controller.read_sensor(slot=0) is True


def test_set_motor_on(controller):
    controller.set_motor(slot=0, state=True)
    assert mock_gpio._get_pin_state(17) == mock_gpio.HIGH


def test_set_motor_off(controller):
    controller.set_motor(slot=0, state=True)
    controller.set_motor(slot=0, state=False)
    assert mock_gpio._get_pin_state(17) == mock_gpio.LOW


def test_all_motors_off(controller):
    controller.set_motor(slot=0, state=True)
    controller.set_motor(slot=1, state=True)
    controller.all_motors_off()
    assert mock_gpio._get_pin_state(17) == mock_gpio.LOW
    assert mock_gpio._get_pin_state(22) == mock_gpio.LOW


def test_raises_if_not_setup():
    cfg = [PinConfig(motor_pin=17, sensor_pin=27)]
    ctrl = GPIOController(cfg)
    with pytest.raises(RuntimeError, match="setup\\(\\)"):
        ctrl.pulse_motor(slot=0, pulses=1)
