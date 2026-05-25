#!/usr/bin/env python3

# author Milan Cizek <milan.cizek@seznam.cz>
# rel. 2026-05-25

import argparse
import logging
import signal
import sys

from termcolor import colored
from tabulate import tabulate

from jsy_modbus import JSYClient, modbus_scan
from jsy_registers import read_sys, read_channel, read_all, set_config
from jsy_enums import all_baudrates


logging.getLogger("pymodbus").setLevel(logging.CRITICAL)


def signal_handler(sig, frame):
    print("Exiting...")
    sys.exit(0)


def modbus_addr(value):
    """
    argparse validator for normal Modbus slave addresses.
    """
    addr = int(value)
    if not 1 <= addr <= 247:
        raise argparse.ArgumentTypeError("Modbus address must be 1..247")
    return addr


def channel_number(value):
    """
    argparse validator for JSY-MK-141G channel numbers.
    """
    ch = int(value)
    if not 1 <= ch <= 6:
        raise argparse.ArgumentTypeError("Channel must be 1..6")
    return ch


def supported_baudrate(value):
    """
    argparse validator for baud rates supported by the device config register.
    """
    baudrate = int(value)
    if baudrate not in all_baudrates():
        supported = ", ".join(map(str, all_baudrates()))
        raise argparse.ArgumentTypeError(f"Unsupported baudrate: {baudrate} (supported: {supported})")
    return baudrate


def positive_float(value):
    """
    argparse validator for positive numeric timeout values.
    """
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than 0")
    return number


def add_connection_args(parser, include_baudrate=True):
    """
    Add common serial connection options to a subcommand.
    """
    parser.add_argument(
        "--device",
        help="Serial device path (defaults to DEVICE from .env/environment or /dev/ttyAMA0)"
    )
    if include_baudrate:
        parser.add_argument(
            "--baudrate",
            type=supported_baudrate,
            help="Baud rate (defaults to BAUD_RATE from .env/environment or 9600)"
        )
    parser.add_argument(
        "--timeout",
        type=positive_float,
        help="Serial response timeout in seconds (defaults to TIMEOUT from .env/environment or 1)"
    )


def print_error(message, exc=None):
    """
    Print a consistent CLI error message.
    """
    print(colored(f"ERROR: {message}", "red"))
    if exc is not None:
        print(str(exc))


def print_key_values(title, data, skip_keys=None):
    """
    Print a simple title followed by aligned key/value pairs.
    """
    skip_keys = set(skip_keys or [])

    print(colored(title, "white", attrs=["bold"]))
    for key, value in data.items():
        if key not in skip_keys:
            print(f"{key:15}: {value}")


def print_channels_table(channels):
    """
    Print decoded channel measurements in a compact table.
    """
    rows = []
    for ch in channels:
        rows.append([
            ch["channel"],
            f"{ch['voltage']:.2f}",
            f"{ch['current']:.4f}",
            ch["power"],
            f"{ch['power_factor']:.3f}",
            f"{ch['frequency']:.2f}",
        ])

    headers = list(map(
        lambda h: colored(h, "white", attrs=["bold"]),
        ["Ch", "Volt[V]", "Curr[A]", "Power[W]", "PF", "Freq[Hz]"]
    ))

    print(tabulate(rows, headers=headers))


def run_scan(args):
    """
    Run the Modbus scan command without opening a fixed-baud client first.
    """
    def scan_progress(event):
        """
        Translate scan progress events into user-facing CLI output.
        """
        if event["type"] == "baud":
            print(colored(f"Switching to: {event['baud']} baud ({event['format']})", "yellow"))

        elif event["type"] == "progress":
            print(f"Progress: {event['percent']:3d} %", end="\r")

        elif event["type"] == "found":
            d = event["device"]
            print(f"  Found device: addr={d['addr']} baud={d['baudrate']}")

        elif event["type"] == "done":
            print(f"Scan finished, devices found: {event['count']}")

    print(colored("Starting Modbus scan...", "white", attrs=["bold"]))

    try:
        tmp_client = JSYClient(device=args.device, timeout=args.timeout)

        devices = modbus_scan(
            device=tmp_client.device,
            smart_scan=not args.full,
            timeout=args.timeout if args.timeout is not None else 0.15,
            progress_cb=scan_progress
        )

    except Exception as e:
        print_error("Scan failed.", e)
        return 1

    for device in devices:
        print(device)

    return 0


def run_sys(cli, args):
    """
    Run the system-info command.
    """
    try:
        data = read_sys(cli, args.addr)
    except Exception as e:
        print_error(f"Unable to read device at address {args.addr}", e)
        return 1

    print_key_values("== System info ==", data)
    return 0


def run_ch(cli, args):
    """
    Run the single-channel read command.
    """
    try:
        channel = read_channel(cli, args.addr, args.ch)
    except Exception as e:
        print_error(f"Unable to read channel {args.ch} at address {args.addr}", e)
        return 1

    print_key_values(f"== Channel {channel['channel']} ==", channel, skip_keys={"channel"})
    return 0


def run_all(cli, args):
    """
    Run the all-channels read command.
    """
    try:
        channels = read_all(cli, args.addr)
    except Exception as e:
        print_error(f"Unable to read all channels at address {args.addr}", e)
        return 1

    print_channels_table(channels)
    return 0


def run_set(cli, args):
    """
    Run the address/baud-rate configuration command.
    """
    if args.new_addr is None and args.new_baudrate is None:
        print(colored("Nothing to change. Use --new-addr and/or --new-baudrate.", "yellow"))
        return 0

    try:
        changed = set_config(
            cli,
            addr=args.addr,
            new_addr=args.new_addr,
            new_baudrate=args.new_baudrate
        )

    except Exception as e:
        print_error(f"Unable to set configuration on device {args.addr}", e)
        return 1

    if changed:
        print(colored("Configuration updated successfully.", "green"))
        print(colored("The device will now respond on the new settings.", "yellow"))
    else:
        print(colored("Configuration unchanged.", "yellow"))

    return 0


def build_arg_parser():
    """
    Build the command-line argument parser.
    """
    parser = argparse.ArgumentParser(
        description="JSY-MK-141G Modbus CLI tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    sub = parser.add_subparsers(
        dest="cmd",
        required=True,
        title="Commands",
    )

    p_scan = sub.add_parser(
        "scan",
        help="Scan Modbus bus for devices"
    )
    add_connection_args(p_scan, include_baudrate=False)
    p_scan.add_argument(
        "--full",
        action="store_true",
        help="Full scan (all baudrates and formats)"
    )

    p_sys = sub.add_parser(
        "sys",
        help="Read system information"
    )
    add_connection_args(p_sys)
    p_sys.add_argument(
        "--addr",
        type=modbus_addr,
        required=True,
        help="Modbus address of the device"
    )

    p_ch = sub.add_parser(
        "ch",
        help="Read one channel"
    )
    add_connection_args(p_ch)
    p_ch.add_argument(
        "--addr",
        type=modbus_addr,
        required=True,
        help="Modbus address of the device"
    )
    p_ch.add_argument(
        "--ch",
        type=channel_number,
        required=True,
        help="Channel number (1..6)"
    )

    p_all = sub.add_parser(
        "all",
        help="Read all channels"
    )
    add_connection_args(p_all)
    p_all.add_argument(
        "--addr",
        type=modbus_addr,
        required=True,
        help="Modbus address of the device"
    )

    p_set = sub.add_parser(
        "set",
        help="Change Modbus address and/or baudrate"
    )
    add_connection_args(p_set, include_baudrate=False)
    p_set.add_argument(
        "--addr",
        type=modbus_addr,
        required=True,
        help="Current Modbus address of the device"
    )
    p_set.add_argument(
        "--baudrate",
        type=supported_baudrate,
        required=True,
        help="Current baudrate used to connect to the device"
    )
    p_set.add_argument(
        "--new-addr",
        type=modbus_addr,
        help="New Modbus address"
    )
    p_set.add_argument(
        "--new-baudrate",
        type=supported_baudrate,
        help="New baudrate to be written into the device"
    )

    return parser


def main():
    """
    Main CLI entry point.
    """
    signal.signal(signal.SIGINT, signal_handler)

    parser = build_arg_parser()
    args = parser.parse_args()

    if args.cmd == "scan":
        return run_scan(args)

    cli = JSYClient(device=args.device, baudrate=args.baudrate, timeout=args.timeout)

    try:
        cli.connect()
    except Exception as e:
        print_error("Unable to open Modbus connection.", e)
        return 1

    try:
        if args.cmd == "sys":
            return run_sys(cli, args)

        elif args.cmd == "ch":
            return run_ch(cli, args)

        elif args.cmd == "all":
            return run_all(cli, args)

        elif args.cmd == "set":
            return run_set(cli, args)

    finally:
        cli.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
