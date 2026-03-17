# chipDispenser

A Raspberry Pi-powered automated poker chip dispenser. Given a dollar amount, the system calculates the optimal chip combination using a greedy algorithm and pulses DC motors to physically dispense the correct chips across up to 4 denomination slots.

## How It Works

1. A `DispenseRequest` is submitted with an amount in cents (e.g. `2500` = $25.00)
2. The `Dispenser` runs a greedy algorithm — largest denominations first — to determine how many of each chip to dispense
3. Inventory is validated before any motors run
4. Each slot's motor is pulsed once per chip, with an IR/optical sensor confirming each chip passes through
5. Inventory counts are decremented and a `DispenseResult` is returned

On non-Pi hardware the system automatically falls back to `MockGPIO` so you can develop and run tests without physical hardware.

## Project Structure

```
chipDispenser/
├── dispenser.py           # Core dispensing logic, greedy algorithm, inventory tracking
├── gpio_controller.py     # Low-level GPIO: motor pulses, sensor reads, emergency stop
├── mock_gpio.py           # MockGPIO drop-in for dev/test without real hardware
├── hardware_config.py     # Pin assignments and default chip denominations — edit to match your wiring
├── test_dispenser.py      # Unit tests for dispensing logic
├── test_gpio_controller.py  # Unit tests for GPIO controller
└── requirements.txt       # Python dependencies
```

## Default Pin Assignments (BCM numbering)

| Slot | Chip     | Value  | Motor Pin | Sensor Pin |
|------|----------|--------|-----------|------------|
| 0    | White    | $1     | 17        | 27         |
| 1    | Red      | $5     | 22        | 23         |
| 2    | Green    | $25    | 24        | 25         |
| 3    | Black    | $100   | 5         | 6          |

Edit `hardware_config.py` to change pin assignments or initial inventory levels.

---

## Running on a Raspberry Pi

### Requirements

- Raspberry Pi (any model with GPIO — Pi 3B+, Pi 4, or Pi Zero 2W recommended)
- Python 3.11+
- Motor driver board (e.g. L298N or similar) wired between GPIO pins and DC motors
- IR or optical sensors (active-LOW) on the sensor pins above

### 1. Install the OS and enable GPIO

Flash Raspberry Pi OS (Lite is fine) and SSH in, or open a terminal. Make sure the system is up to date:

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Python 3.11+

Raspberry Pi OS Bookworm ships with Python 3.11. Verify:

```bash
python3 --version
```

If you need a newer version, use `pyenv` or build from source.

### 3. Clone the repository

```bash
git clone https://github.com/crobicha/chipDispenser.git
cd chipDispenser
```

### 4. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

Then uncomment and install the RPi.GPIO package (required for real hardware):

```bash
pip install RPi.GPIO
```

Or edit `requirements.txt`, uncomment `# RPi.GPIO>=0.7.1`, and re-run `pip install -r requirements.txt`.

### 6. Configure pin assignments

Edit `hardware_config.py` to match your physical wiring:

```python
PIN_CONFIGS: list[PinConfig] = [
    PinConfig(motor_pin=17, sensor_pin=27),   # Slot 0 — White  $1
    PinConfig(motor_pin=22, sensor_pin=23),   # Slot 1 — Red    $5
    ...
]
```

All pin numbers use BCM (Broadcom) numbering.

### 7. Run the tests

```bash
pytest test_dispenser.py test_gpio_controller.py -v
```

Tests use `MockGPIO` and do not require physical hardware.

### 8. Run the API server

The project includes FastAPI and Uvicorn. Start the server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

> **Note:** A `main.py` entry point with the FastAPI `app` instance is required. See the API section below for the expected structure.

To run on boot, create a systemd service:

```bash
sudo nano /etc/systemd/system/chipdispenser.service
```

```ini
[Unit]
Description=Chip Dispenser API
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/chipDispenser
ExecStart=/home/pi/chipDispenser/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable chipdispenser
sudo systemctl start chipdispenser
```

---

## Development (non-Pi)

No hardware required. `MockGPIO` is used automatically when `RPi.GPIO` is not installed.

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -v
```

---

## Key Components

### `Dispenser`

```python
from hardware.gpio_controller import GPIOController
from hardware.dispenser import Dispenser, DispenseRequest
from hardware_config import PIN_CONFIGS, DEFAULT_DENOMINATIONS

gpio = GPIOController(PIN_CONFIGS)
gpio.setup()

dispenser = Dispenser(gpio, DEFAULT_DENOMINATIONS)
result = await dispenser.dispense(DispenseRequest(amount_cents=2500))
print(result)  # DispenseResult(success=True, dispensed={'green': 1}, total_value=2500)
```

### `GPIOController`

- `setup()` — initialize all GPIO pins
- `pulse_motor(slot, pulses)` — dispense chips from a slot (100ms ON / 50ms OFF per pulse)
- `read_sensor(slot)` — returns `True` if a chip is detected (active-LOW sensor)
- `all_motors_off()` — emergency stop
- `teardown()` — release GPIO resources

---

## Future Plans

- REST API endpoints (FastAPI scaffolding already included)
- Payment processor integration (Stripe / Square)
- RFID card reader support (`mfrc522`)
- Inventory management dashboard
