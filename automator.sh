#!/bin/bash
#A* -------------------------------------------------------------------
#B* A simple wrapper script for running automation tasks more smoothly
#-* without needing to know the exact python interpreter path
#C* Copyright 2025 by Martin Urban.
#D* -------------------------------------------------------------------
#E* It is unlawful to modify or remove this copyright notice.
#F* -------------------------------------------------------------------
#G* Please see the accompanying LICENSE file for further information.
#H* -------------------------------------------------------------------
#I* Additional authors of this source file include:
#-*
#-*
#-*
#Z* -------------------------------------------------------------------
cd "$(dirname "$0")" || exit 1
if [ ! -x ./.venv/bin/python ]; then
    echo "Virtual environment does not exist yet! Please create it first (see README.md)." >&2
    exit 1
fi
exec ./.venv/bin/python ./automations/my_automator.py "$@"
