"""
#A* -------------------------------------------------------------------
#B* This file contains source code for running automation tasks related
#-* to the build process of the PyMOL computer program
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
"""
import build_exe
import build_inno_setup
import tasks


# "setup" (creates .venv) is handled by automator.sh / win_automator.bat, because
# this script needs the .venv to run.
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
      },
      "packages": {
        "help": "Creates the installer/packages of this platform (run 'build app' first)",
        "func": tasks.build_packages
      },
      "all": {
        "help": "Creates the frozen application and the installer/packages of this platform",
        "func": tasks.build_all
      }
    }
  },
  "test": {
    "help": "Runs the headless smoke test with the frozen application",
    "func": tasks.test,
    "subcommands": {
      "gui": {
        "help": "Runs the smoke test with the Qt GUI (needs a display)",
        "func": tasks.test_gui
      }
    }
  }
}


if __name__ == "__main__":
  from task_automator import automator
  automator.Automator(AUTOMATION_TREE).run()
