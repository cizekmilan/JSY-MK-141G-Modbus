# ⚡ JSY-MK-141G

> Python CLI tool for reading JSY-MK-141G 6-channel energy meter values over Modbus RTU.

# 🎯 Overview

This project provides a small Python command-line tool for working with the JSY-MK-141G multi-channel energy meter over Modbus RTU.

The JSY-MK-141G is a 6-channel electrical measurement module. It exposes measured values through a Modbus RTU serial interface, making it useful for small monitoring setups, Raspberry Pi projects, home-lab measurements, and other systems where electrical values need to be read programmatically.

This tool focuses on the values exposed by the device registers, including voltage, current, active power, power factor, and frequency for individual measurement channels.

The main goal is to make the measured values easy to read from a Raspberry Pi or another Linux device connected to the meter through a serial/RS485 interface.

The primary workflow is reading live electrical measurements from one configured device.

The project currently supports:

* reading device system information
* reading one measurement channel
* reading all six measurement channels
* a small optional Bash demo using `mbpoll`

It also includes a few extra utility features that are useful during setup or troubleshooting:

* scanning the Modbus bus for devices
* changing the device Modbus address and baud rate

The Python implementation is the primary part of the project. The Bash script in `examples/` is only a lightweight alternative for quick testing and comparison.

# 📏 Measured Values

For each of the six channels, the tool can read:

* voltage `[V]`
* current `[A]`
* active power `[W]`
* power factor `[-]`
* frequency `[Hz]`

# 🗂️ Project Structure

```text
/
├── jsy_mk_cli.py              # Python CLI entry point
├── jsy_modbus.py              # Low-level Modbus RTU communication
├── jsy_registers.py           # Register map, decoding, and configuration writes
├── jsy_enums.py               # Device enum/value mappings
├── requirements.txt           # Python dependencies
├── .env.example               # Example local configuration
├── _run_demo_cli.sh           # Local venv bootstrap/demo script
├── examples/
│   └── mbpoll_demo.sh         # Optional Bash demo using mbpoll
└── docs/
    ├── manuals/               # User manuals and supplemental notes
    ├── original-software/     # Vendor/original reference software
    └── photos/                # Optional hardware/setup photos
```

# ⚙️ Requirements

Python dependencies:

```text
pyserial
pymodbus
python-dotenv
termcolor
tabulate
```

Install them with:

```bash
python3 -m pip install -r requirements.txt
```

For the optional Bash/`mbpoll` demo:

```bash
sudo apt install mbpoll
```

The examples below run shell scripts through `bash`, so executable permissions are not required. If you prefer running them directly, make them executable:

```bash
chmod +x _run_demo_cli.sh examples/mbpoll_demo.sh
```

# 🔧 Configuration

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Example configuration:

```env
DEVICE="/dev/ttyAMA0"
BAUD_RATE=9600
TIMEOUT=1
```

Configuration values can also be provided through environment variables or overridden by CLI options where supported.

The Modbus slave address is passed per command with `--addr`.

The example configuration assumes the factory/default connection settings:

```text
baud rate: 9600
Modbus address: 1 (0x01)
```

If your device has already been reconfigured, update `BAUD_RATE` in `.env` and use the current device address with `--addr`.

# 🚀 Usage

```bash
# Read system information
python3 jsy_mk_cli.py sys --addr 1

# Read one channel
python3 jsy_mk_cli.py ch --addr 1 --ch 1

# Read all channels
python3 jsy_mk_cli.py all --addr 1

# Scan the Modbus bus
python3 jsy_mk_cli.py scan

# Full scan with all supported baud rates and serial formats
python3 jsy_mk_cli.py scan --full

# Change Modbus address and/or baud rate
python3 jsy_mk_cli.py set --addr 1 --baudrate 9600 --new-addr 2 --new-baudrate 38400
```

After changing the configuration, the device responds using the new address and/or baud rate.

# 🔌 Connection Options

Most commands can override the local `.env` settings:

```bash
python3 jsy_mk_cli.py all --device /dev/ttyUSB0 --baudrate 38400 --timeout 1 --addr 2
```

Supported baud rates:

```text
1200, 2400, 4800, 9600, 19200, 38400
```

# 🔎 Scan Modes

The scan command is mainly a setup/troubleshooting helper.

Default scan:

```bash
python3 jsy_mk_cli.py scan
```

The default scan is faster. It checks the likely JSY-MK communication format `8N1` and baud rates from `9600` upward.

Full scan:

```bash
python3 jsy_mk_cli.py scan --full
```

The full scan is slower, but useful when the device configuration is unknown. It tries all supported baud rates and several serial formats:

```text
8N1, 8E1, 8O1, 8N2
```

# 🧪 Local Demo Script

The helper script `_run_demo_cli.sh` creates or reuses a local `.venv`, installs dependencies, and runs a few demo commands.

```bash
bash _run_demo_cli.sh
```

The script also checks whether an existing virtual environment still points to a valid location. This is useful if the project directory was moved.

# 🧰 Optional mbpoll Demo

The repository also includes a small Bash alternative:

```bash
bash examples/mbpoll_demo.sh sys
bash examples/mbpoll_demo.sh ch 1
bash examples/mbpoll_demo.sh all
```

This script keeps its connection settings directly at the top of the file and uses `mbpoll` instead of the Python Modbus stack.

# 📚 Documentation

The `docs/` directory contains reference material collected for this device:

* `docs/manuals/` - user manuals and supplemental address/baud-rate modification instructions
* `docs/original-software/` - vendor/original reference software and GUI screenshot

The original software files are included only as reference material for this specific device.

# 📝 Notes

The project is intentionally small and script-oriented. It does not aim to be a full Modbus framework.

The most important implementation files are:

* `jsy_modbus.py` - serial connection and raw Modbus register access
* `jsy_registers.py` - register addresses, scaling, decoded values, and configuration writes
* `jsy_mk_cli.py` - command-line interface and output formatting

# 📄 License

This project is provided free of charge for personal, educational, and experimental use.

The included vendor/original software and documentation files are provided only as reference material for the JSY-MK-141G device.
