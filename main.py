import time
from hardware.gpio_controller import GPIOController
from hardware.hardware_config import PIN_CONFIGS

controller = GPIOController(PIN_CONFIGS)
controller.setup()

controller.set_motor(slot=0, state=True)
time.sleep(2)
controller.set_motor(slot=0, state=False)

controller.teardown()
