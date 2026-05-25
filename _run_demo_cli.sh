#!/bin/bash

# author Milan Cizek <milan.cizek@seznam.cz>
# rel. 2026-05-25

PY_ENV_NAME=".venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"


### --- Virtual environment ---

# Check whether the virtual environment exists and is still valid.
# This catches cases where the project directory was moved and activate
# still points to the old location.
if [ -d "$PY_ENV_NAME" ]; then
  if [ -f "$PY_ENV_NAME/bin/activate" ]; then

    # Test activate in a subshell so the current shell environment stays clean.
    VENV_PATH=$(bash -c "source '$PY_ENV_NAME/bin/activate' >/dev/null 2>&1 && echo \"\$VIRTUAL_ENV\"")

    if [ -z "$VENV_PATH" ] || [ ! -d "$VENV_PATH" ]; then
      echo "Virtual environment is invalid or points to a missing location. Recreating..."
      rm -rf "$PY_ENV_NAME"
    fi
  else
    echo "Virtual environment is incomplete; activate script not found. Recreating..."
    rm -rf "$PY_ENV_NAME"
  fi
fi

# Create the virtual environment if it does not exist or was removed above.
if [ ! -d "$PY_ENV_NAME" ]; then
  "$PYTHON_BIN" -m venv "$PY_ENV_NAME"
else
  echo "Virtual environment $PY_ENV_NAME already exists, skipping creation."
fi


source "$PY_ENV_NAME/bin/activate"

  # upgrade pip and install project dependencies
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt

  ### --- Demo commands ---

  # system info
  python jsy_mk_cli.py sys --addr 1
  python jsy_mk_cli.py sys --addr 2
  echo

  # one channel
  python jsy_mk_cli.py ch --addr 2 --ch 1
  echo

  # all channels
  python jsy_mk_cli.py all --addr 1
  python jsy_mk_cli.py all --addr 2
  echo

  # scan
  python jsy_mk_cli.py scan
  echo

  # change address/baud rate example:
  # python jsy_mk_cli.py set --addr 1 --baudrate 9600 --new-addr 3 --new-baudrate 38400

deactivate
