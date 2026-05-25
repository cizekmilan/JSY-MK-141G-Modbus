#!/usr/bin/env python3

# author Milan Cizek <milan.cizek@seznam.cz>
# rel. 2026-05-25

from jsy_modbus import JSYClient
from jsy_enums import baudrate_to_regval, BAUD_RATES


SYSTEM_INFO_REG = 0x0000
CONFIG_REG = 0x0004
CHANNEL_BASE_REG = 0x0040
CHANNEL_REG_STRIDE = 0x0D
CHANNEL_COUNT = 6
CHANNEL_REGISTER_COUNT = 7

FACTORY_MODBUS_ADDR = 1
FACTORY_BAUDRATE = 9600


def validate_modbus_addr(addr: int):
    """
    Validate the normal Modbus slave address range.
    """
    if not 1 <= addr <= 247:
        raise ValueError("Modbus address must be 1..247")


def read_sys(client: JSYClient, addr: int):
    """
    Read device system information such as model, ranges, and config.
    """
    validate_modbus_addr(addr)

    regs = client.read_registers(SYSTEM_INFO_REG, 5, addr)

    return {
        "model": regs[0],
        "voltage_range": regs[2],
        "current_range": regs[3],
        "config_raw": regs[4],
        "modbus_addr": addr,
        "baudrate": client.baudrate,
    }


def read_channel(client: JSYClient, addr: int, ch: int):
    """
    Read decoded measurements from one channel.
    """
    validate_modbus_addr(addr)

    if not 1 <= ch <= CHANNEL_COUNT:
        raise ValueError(f"Channel must be 1..{CHANNEL_COUNT}")

    base = CHANNEL_BASE_REG + (ch - 1) * CHANNEL_REG_STRIDE

    regs = client.read_registers(base, CHANNEL_REGISTER_COUNT, addr)

    return {
        "channel": ch,
        "voltage": regs[0] / 100.0,
        "current": regs[1] / 100.0,
        "power": regs[2],
        "power_factor": regs[5] / 1000.0,
        "frequency": regs[6] / 100.0,
    }


def read_all(client: JSYClient, addr: int):
    """
    Read decoded measurements from all channels.
    """
    validate_modbus_addr(addr)

    return [read_channel(client, addr, ch) for ch in range(1, CHANNEL_COUNT + 1)]


def set_config(client: JSYClient, addr: int, new_addr=None, new_baudrate=None):
    """
    Write a new Modbus address and/or baud rate to configuration register 0x0004.
    """
    validate_modbus_addr(addr)

    if new_addr is None and new_baudrate is None:
        return False

    current = client.read_registers(CONFIG_REG, 1, addr)[0]

    if new_addr is None:
        new_addr = current >> 8
    else:
        validate_modbus_addr(new_addr)

    if new_baudrate is None:
        code = current & 0xFF
        new_baudrate = None
        for baudrate, reg in BAUD_RATES.items():
            if reg == code:
                new_baudrate = baudrate
                break

        if new_baudrate is None:
            raise RuntimeError(f"Unknown baudrate code in device config: {code}")

    baud_code = baudrate_to_regval(new_baudrate)
    reg_value = (new_addr << 8) | baud_code

    client.write_register(CONFIG_REG, reg_value, addr)
    return True


def set_default(client: JSYClient, addr: int):
    """
    Restore the default device address and baud rate.
    """
    return set_config(
        client,
        addr,
        new_addr=FACTORY_MODBUS_ADDR,
        new_baudrate=FACTORY_BAUDRATE,
    )
