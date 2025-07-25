# remotePi

A Raspberry Pi robot control server with async socket interface and GPIO motor control.

## Features
- Async TCP server for remote control
- Motor and direction control via GPIO
- Physical reset switch
- Modular hardware abstraction

## Usage
1. Install dependencies: `pip install -r requirements.txt`
2. Run: `python3 remotePiMain.py`
3. Connect via TCP on port 9999 and send commands like `L:1`, `R:-1`, `reset`.

## Configuration
Edit constants in `remotePiMain.py` or use a config file.

## SystemD
See `Init_SystemD_Files/` for service setup.