#!/usr/bin/env python3

# author Milan Cizek <milan.cizek@seznam.cz>
# rel. 2026-05-25

# Baud rate value mapping used by device configuration register 0x0004.
BAUD_RATES = {
    1200: 1,
    2400: 3,
    4800: 4,
    9600: 6,
    19200: 7,
    38400: 8,
}


def baudrate_to_regval(baudrate: int) -> int:
    """
    Convert a baud rate to the value stored in the configuration register.
    """
    try:
        return BAUD_RATES[baudrate]
    except KeyError:
        raise ValueError(f"Unsupported baudrate: {baudrate}")


def all_baudrates():
    """
    Return all supported baud rates sorted from lowest to highest.
    """
    return sorted(BAUD_RATES.keys())
