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
import build_exe
import build_inno_setup


AUTOMATION_TREE = {
  "build": {
    "help": "Build targets",
    "subcommands": {
      "app": {
        "help": "Creates a frozen Python application",
        "func": build_exe.build
      },
      "inno_setup": {
        "help": "Creates the Inno Setup installer for Windows (run 'build app' first)",
        "func": build_inno_setup.build
      }
    }
  }
}


if __name__ == "__main__":
  from task_automator import automator
  automator.Automator(AUTOMATION_TREE).run()
