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
if [ -d "./.venv/bin" ]; then
    # Default behavior: Run automations.py
    ./.venv/bin/python ./automations/my_automator.py "$@"
else
    echo "Virtual environment does not exist yet! Please run create a one."
fi
