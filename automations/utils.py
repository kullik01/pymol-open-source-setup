"""
#A* -------------------------------------------------------------------
#B* This file contains source code for running automation tasks related
#-* to the build process of the PyMOL computer program
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
"""
import subprocess
import sys


def run(args: list, **kwargs) -> None:
  """Runs a command and aborts the automation if it fails.

  Args:
    args: The command and its arguments.
    **kwargs: Passed on to subprocess.run (e.g. cwd, env).
  """
  tmp_result = subprocess.run([str(arg) for arg in args], **kwargs)
  if tmp_result.returncode != 0:
    sys.exit(f"Command failed with exit code {tmp_result.returncode}: {args[0]}")
