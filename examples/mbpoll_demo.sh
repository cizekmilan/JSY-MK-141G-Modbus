#!/bin/bash

# author Milan Cizek <milan.cizek@seznam.cz>
# rel. 2026-05-24
# required: apt -y install mbpoll

# Connection defaults. Change these values to match your Modbus bus.
DEVICE="/dev/ttyAMA0"
BAUD_RATE=9600
MODBUS_ADDR=1
TIMEOUT=1


### --- Helpers ---

error() {
  echo "ERROR: $*" >&2
}

# Print short command help. Do not touch the Modbus bus from here.
usage() {
  echo "Usage:"
  echo "  $0 sys        - read system info"
  echo "  $0 ch <1..6>  - read channel parameters"
  echo "  $0 all        - read all channels in table"
}

# mbpoll uses 1-based register references, while the datasheet uses 0-based addresses.
ref() {
  echo $(( $1 + 1 ))
}

# Convert a hexadecimal register value (with or without 0x) to decimal.
hex2dec() {
  local HEX="${1#0x}"

  # Catch empty or malformed mbpoll output early.
  if [[ ! "$HEX" =~ ^[0-9A-Fa-f]+$ ]]; then
    error "Invalid hex value: ${1:-<empty>}"
    return 1
  fi

  printf "%d" "0x$HEX"
}

# Convert and scale a hexadecimal register value using awk floating-point math.
scale_hex() {
  HEX_VALUE=$1
  DIVISOR=$2
  PRECISION=$3

  DEC_VALUE=$(hex2dec "$HEX_VALUE") || return 1

  awk -v VALUE="$DEC_VALUE" -v DIVISOR="$DIVISOR" -v PRECISION="$PRECISION" \
    'BEGIN { printf "%.*f", PRECISION, VALUE / DIVISOR }'
}

# Read holding registers and return only the mbpoll data lines.
read_regs() {
  START_REG=$1
  COUNT=$2

  RAW=$(mbpoll -1 -m rtu \
        -a "$MODBUS_ADDR" -b "$BAUD_RATE" \
        -P none \
        -t 4:hex \
        -r "$(ref "$START_REG")" \
        -c "$COUNT" \
        -o "$TIMEOUT" \
        "$DEVICE" 2>/dev/null)

  # Keep mbpoll stderr hidden, but report enough context for troubleshooting.
  if [[ $? -ne 0 ]]; then
    error "mbpoll read failed (device=$DEVICE, addr=$MODBUS_ADDR, baud=$BAUD_RATE, reg=0x$(printf '%04X' "$START_REG"), count=$COUNT)"
    return 1
  fi

  # Register rows start with "[...]" in mbpoll output.
  RAW_LINES=$(echo "$RAW" | grep "^\[" || true)
  LINE_COUNT=$(echo "$RAW_LINES" | grep -c "^\[" || true)

  if [[ "$LINE_COUNT" -ne "$COUNT" ]]; then
    error "Unexpected mbpoll response: got $LINE_COUNT registers, expected $COUNT"
    return 1
  fi

  echo "$RAW_LINES"
}

# Extract one register value from previously filtered mbpoll data lines.
reg_value() {
  RAW_LINES=$1
  INDEX=$2

  echo "$RAW_LINES" | sed -n "${INDEX}p" | awk '{print $2}'
}


### --- Modbus availability ---

# Fail fast before running commands that need a live device.
modbus_check() {
  if ! read_regs 0x0000 1 >/dev/null 2>&1; then
    printf "ERROR: Modbus device not responding (device=%s, addr=0x%02X, baud=%d)\n" \
      "$DEVICE" "$MODBUS_ADDR" "$BAUD_RATE"
    exit 1
  fi
}


### --- Read system info ---

# Read model/range/config registers from the fixed system-info block.
read_sys() {
  echo "== System info =="

  RAW_LINES=$(read_regs 0x0000 5) || return 1

  MODEL_HEX=$(reg_value "$RAW_LINES" 1)
  VOLT_RANGE_HEX=$(reg_value "$RAW_LINES" 3)
  CURR_RANGE_HEX=$(reg_value "$RAW_LINES" 4)
  CONFIG_HEX=$(reg_value "$RAW_LINES" 5)

  MODEL=$(hex2dec "$MODEL_HEX") || return 1
  VOLT_RANGE=$(hex2dec "$VOLT_RANGE_HEX") || return 1
  CURR_RANGE=$(hex2dec "$CURR_RANGE_HEX") || return 1

  echo "Model:         $MODEL"
  echo "MODBUS addr.:  ${MODBUS_ADDR}"
  echo "Baud rate:     ${BAUD_RATE}"
  echo "Voltage range: ${VOLT_RANGE} V"
  echo "Current range: ${CURR_RANGE} A"
  echo "Config raw:    ${CONFIG_HEX}"
}


### --- Read one channel ---

# Read and decode one channel measurement block.
read_ch() {
  CH=$1

  if [[ ! "$CH" =~ ^[0-9]+$ ]] || [[ $CH -lt 1 || $CH -gt 6 ]]; then
    error "Channel must be 1..6"
    return 1
  fi

  BASE=$((0x0040 + (CH - 1) * 0x0D))
  COUNT=7

  RAW_LINES=$(read_regs "$BASE" "$COUNT") || return 1

  V_HEX=$(reg_value "$RAW_LINES" 1)
  I_HEX=$(reg_value "$RAW_LINES" 2)
  P_HEX=$(reg_value "$RAW_LINES" 3)
  PF_HEX=$(reg_value "$RAW_LINES" 6)
  F_HEX=$(reg_value "$RAW_LINES" 7)

  VOLT=$(scale_hex "$V_HEX" 100 2) || return 1
  CURR=$(scale_hex "$I_HEX" 100 4) || return 1
  POWR=$(hex2dec "$P_HEX") || return 1
  PF=$(scale_hex "$PF_HEX" 1000 3) || return 1
  FREQ=$(scale_hex "$F_HEX" 100 2) || return 1

  printf "== Channel %d ==\n" "$CH"
  printf "Voltage:      %.2f V\n" "$VOLT"
  printf "Current:      %.4f A\n" "$CURR"
  printf "Power:        %d W\n" "$POWR"
  printf "Power factor: %.3f\n" "$PF"
  printf "Frequency:    %.2f Hz\n" "$FREQ"
}


### --- Read all 6 channels in a table ---

# Poll all channel blocks one by one and print a compact overview.
read_all() {
  printf "== All channels ==\n"
  printf "%-3s %-8s %-8s %-8s %-6s %-8s\n" "Ch" "Volt[V]" "Curr[A]" "Power[W]" "PF" "Freq[Hz]"
  printf "%-3s %-8s %-8s %-8s %-6s %-8s\n" "---" "--------" "--------" "--------" "------" "--------"

  for CH in 1 2 3 4 5 6; do
    BASE=$((0x0040 + (CH - 1) * 0x0D))
    COUNT=7

    RAW_LINES=$(read_regs "$BASE" "$COUNT") || return 1

    V_HEX=$(reg_value "$RAW_LINES" 1)
    I_HEX=$(reg_value "$RAW_LINES" 2)
    P_HEX=$(reg_value "$RAW_LINES" 3)
    PF_HEX=$(reg_value "$RAW_LINES" 6)
    F_HEX=$(reg_value "$RAW_LINES" 7)

    VOLT=$(scale_hex "$V_HEX" 100 2) || return 1
    CURR=$(scale_hex "$I_HEX" 100 4) || return 1
    POWR=$(hex2dec "$P_HEX") || return 1
    PF=$(scale_hex "$PF_HEX" 1000 3) || return 1
    FREQ=$(scale_hex "$F_HEX" 100 2) || return 1

    printf "%-3d %-8.2f %-8.4f %-8d %-6.3f %-8.2f\n" \
      "$CH" "$VOLT" "$CURR" "$POWR" "$PF" "$FREQ"
  done
}


### --- MAIN ---

# Keep help/usage independent from device access; only data commands call modbus_check.
case "$1" in
  sys)
    modbus_check
    read_sys
    ;;
  ch)
    modbus_check
    read_ch "$2"
    ;;
  all)
    modbus_check
    read_all
    ;;
  ""|-h|--help)
    usage
    exit 0
    ;;
  *)
    usage
    exit 1
    ;;
esac
