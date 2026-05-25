#!/usr/bin/env python3

# author Milan Cizek <milan.cizek@seznam.cz>
# rel. 2026-05-25

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from pymodbus.client.serial import ModbusSerialClient

from jsy_enums import all_baudrates


ENV_FILE = Path(__file__).resolve().with_name(".env")
load_dotenv(ENV_FILE)

DEVICE = os.getenv("DEVICE", "/dev/ttyAMA0")
BAUDRATE = os.getenv("BAUD_RATE", "9600")
TIMEOUT = os.getenv("TIMEOUT", "1")

DEFAULT_PARITY = "N"
DEFAULT_STOPBITS = 1
DEFAULT_BYTESIZE = 8

SMART_SCAN_FORMATS = [
    (DEFAULT_PARITY, DEFAULT_STOPBITS),
]

FULL_SCAN_FORMATS = [
    (DEFAULT_PARITY, DEFAULT_STOPBITS),
    ("E", 1),
    ("O", 1),
    ("N", 2),
]


class JSYClient:
    """
    Low-level Modbus RTU client for the JSY-MK-141G meter.
    """

    def __init__(self, device=None, baudrate=None, timeout=None):
        self.device = device or DEVICE
        self.baudrate = int(baudrate or BAUDRATE)
        self.timeout = float(timeout or TIMEOUT)

        self.client = ModbusSerialClient(
            port=self.device,
            baudrate=self.baudrate,
            parity=DEFAULT_PARITY,
            stopbits=DEFAULT_STOPBITS,
            bytesize=DEFAULT_BYTESIZE,
            timeout=self.timeout,
            retries=0,
        )

    def connect(self):
        """
        Open the serial Modbus connection.
        """
        if not self.client.connect():
            raise RuntimeError("Failed to connect to Modbus device")

    def close(self):
        """
        Close the serial Modbus connection.
        """
        self.client.close()

    def read_registers(self, addr, count, slave):
        """
        Read holding registers.
        """
        rr = self.client.read_holding_registers(
            address=addr,
            count=count,
            slave=slave,
        )

        if rr is None:
            raise RuntimeError(f"No response from device (addr=0x{addr:04X})")

        if rr.isError():
            raise RuntimeError(f"Modbus error: {rr}")

        return rr.registers

    def write_register(self, addr, value, slave):
        """
        Write one holding register.
        """
        rr = self.client.write_registers(
            address=addr,
            values=[value],
            slave=slave,
        )

        if rr is None:
            raise RuntimeError(f"No response from device while writing (addr=0x{addr:04X})")

        if rr.isError():
            raise RuntimeError(f"Write failed: {rr}")


def modbus_scan(device, smart_scan=True, addr_start=1, addr_end=247, timeout=0.15, progress_cb=None):
    """
    Scan the Modbus bus and return detected devices.
    """

    # Smart scan uses the likely JSY-MK format only; full scan tries extra serial formats.
    if smart_scan:
        baudrate_list = [b for b in all_baudrates() if b >= 9600]
        formats = SMART_SCAN_FORMATS
    else:
        baudrate_list = all_baudrates()
        formats = FULL_SCAN_FORMATS

    found = []

    total_steps = len(formats) * len(baudrate_list) * (addr_end - addr_start + 1)
    done_steps = 0

    for parity, stopbits in formats:
        fmt_str = f"8{parity}{stopbits}"

        for baudrate in baudrate_list:

            if progress_cb:
                progress_cb({
                    "type": "baud",
                    "baud": baudrate,
                    "format": fmt_str
                })

            client = JSYClient(device=device, baudrate=baudrate, timeout=timeout)

            try:
                client.connect()

                for addr in range(addr_start, addr_end + 1):
                    try:
                        # A successful read from the model register is enough to identify a live slave.
                        rr = client.client.read_holding_registers(
                            address=0x0000,
                            count=1,
                            slave=addr,
                        )

                        if rr and not rr.isError():
                            device_info = {
                                "addr": addr,
                                "baudrate": baudrate,
                                "format": fmt_str,
                            }
                            found.append(device_info)

                            if progress_cb:
                                progress_cb({
                                    "type": "found",
                                    "device": device_info
                                })

                    except Exception:
                        # Most addresses will time out during a scan; keep probing the rest of the bus.
                        pass

                    done_steps += 1

                    if progress_cb:
                        percent = int((done_steps / total_steps) * 100)
                        progress_cb({
                            "type": "progress",
                            "percent": percent
                        })

                    time.sleep(0.01)

            finally:
                client.close()

    if progress_cb:
        progress_cb({
            "type": "done",
            "count": len(found)
        })

    return found
