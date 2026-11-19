#!/bin/bash
#A* -------------------------------------------------------------------
#B* A simple wrapper script for running automation tasks more smoothly
#-* without needing to know the exact python interpreter path
#C* Copyright 2026 by Martin Urban.
#D* -------------------------------------------------------------------
#E* It is unlawful to modify or remove this copyright notice.
#F* -------------------------------------------------------------------
#G* Please see the accompanying LICENSE file for further information.
#H* -------------------------------------------------------------------
#I* Additional authors of this source file include:
#-* Hannah Kullik
#-*
#-*
#Z* -------------------------------------------------------------------
cd "$(dirname "$0")" || exit 1
# "setup" creates .venv with Python 3.11 and installs requirements.txt
if [ "${1:-}" = "setup" ]; then
    if ! command -v uv >/dev/null; then
        echo "uv is missing, see https://docs.astral.sh/uv/getting-started/installation/" >&2
        exit 1
    fi
    uv venv --allow-existing --python 3.11 .venv && exec uv pip install --compile-bytecode --python .venv -r requirements.txt
fi
if [ ! -x ./.venv/bin/python ]; then
    echo "The virtual environment does not exist yet. Create it with: ./automator.sh setup" >&2
    exit 1
fi
exec ./.venv/bin/python ./automations/my_automator.py "$@"
