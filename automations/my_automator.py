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
import dev_env


AUTOMATION_TREE = {
  # fixme: This can likely be replaced with a simple "pip install -r requirements.txt"
  # "setup": {
  #   "help": "Setup automations",
  #   "subcommands": {
  #     "dev-env": {
  #       "help": "Sets up the development environment",
  #       "func": dev_env.setup_dev_env
  #     }
  #   }
  # },
  "build": {
    "help": "Build targets",
    "subcommands": {
      "app": {
        "help": "Creates a frozen Python application",
        "func": build_exe.build
      },
      "inno_setup": {
        "help": "Creates the Inno setup for the Windows installation",
        "func": build_inno_setup.build
      },
      "inno_setup_ci": {
        "help": "Creates the Inno setup for the Windows installation in the Windows GitHub action runner (CI)",
        "func": build_inno_setup.build_for_ci
      }
    }
  }
}


if __name__ == "__main__":
  from task_automator import automator
  automator.Automator(AUTOMATION_TREE).run()
