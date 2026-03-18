import time
from hardware.gpio_controller import GPIOController, IS_REAL_PI
from hardware.hardware_config import PIN_CONFIGS

print(IS_REAL_PI)   # Should now be True

controller = GPIOController(PIN_CONFIGS)
controller.setup()
controller.set_motor(slot=0, state=True)   # M1 should spin



time.sleep(2)
controller.set_motor(slot=0, state=False)   # M1 should spin