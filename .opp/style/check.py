"""Run the OPP family's style checker: ``python3 .opp/style/check.py --help``.

``opp-workflow style-install`` installs this file with the ``opp_style``
package beside it. The script makes its own folder importable, so it runs
with any ``python3`` from 3.9 on, with no packages installed.
"""

from __future__ import annotations

import importlib
import os
import sys


def main() -> int:
    """Make this folder importable and run the checker's command line.

    Returns:
        The checker's exit status.
    """
    # The copy is committed; compiled caches beside it would only be clutter.
    sys.dont_write_bytecode = True
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    tmp_cli = importlib.import_module("opp_style.cli")
    return tmp_cli.main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
