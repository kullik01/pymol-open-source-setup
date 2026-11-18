#!/usr/bin/env bash
# Pass all arguments to the Python script in the project's virtual environment.
project_dir="$(dirname "$0")"
if [ ! -x "$project_dir/.venv/bin/python" ]; then
    echo "Virtual environment does not exist. Create .venv and install the platform requirements first." >&2
    exit 1
fi
exec "$project_dir/.venv/bin/python" "$project_dir/pymakefile.py" "$@"
