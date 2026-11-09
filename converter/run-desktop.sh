#!/bin/sh
cd "$(dirname "$0")/.."
if [ -x .venv/bin/python ]; then exec .venv/bin/python converter/desktop.py; fi
exec python3 converter/desktop.py
