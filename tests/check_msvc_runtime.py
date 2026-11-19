"""Checks that a frozen Windows app ships every Microsoft C++ runtime DLL it imports.

Reads the imported DLLs of every .exe, .dll and .pyd in the app and fails if a
runtime DLL (vcruntime140*.dll, msvcp140*.dll, ...) is neither next to the
executable nor next to the importing file. Without them the app does not start
on PCs that have no VC++ Redistributable installed.

Usage: python tests/check_msvc_runtime.py <directory of the frozen app>
Requires lief (part of requirements.txt on Windows).
"""
import pathlib
import re
import sys

import lief


RUNTIME_DLL_PATTERN = re.compile(
  r"^(vcruntime140(_\d+)?|msvcp140(_\w+)?|concrt140|vcomp140|vccorlib140|vcamp140)\.dll$",
  re.IGNORECASE,
)


def main() -> int:
  if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <directory of the frozen app>", file=sys.stderr)
    return 2
  app_dir = pathlib.Path(sys.argv[1])
  lief.logging.disable()

  imported_by = {}  # runtime DLL name (lower case) -> files importing it
  missing = []
  binaries = [p for p in app_dir.rglob("*") if p.suffix.lower() in (".exe", ".dll", ".pyd")]
  for binary_path in binaries:
    binary = lief.PE.parse(str(binary_path))
    if binary is None:
      continue
    for imported in binary.imports:
      name = imported.name.lower()
      if not RUNTIME_DLL_PATTERN.match(name):
        continue
      imported_by.setdefault(name, []).append(binary_path)
      shipped = (app_dir / name).exists() or (binary_path.parent / name).exists()
      if not shipped:
        missing.append((name, binary_path.relative_to(app_dir)))

  print(f"Checked {len(binaries)} files; imported runtime DLLs:")
  for name in sorted(imported_by):
    print(f"  {name}: imported by {len(imported_by[name])} files")
  if missing:
    print("Missing runtime DLLs:", file=sys.stderr)
    for name, importer in sorted(set(missing)):
      print(f"  {name} (needed by {importer})", file=sys.stderr)
    return 1
  if not imported_by:
    print("No runtime DLL imports found - is this a frozen Windows app?", file=sys.stderr)
    return 1
  print("All imported runtime DLLs are shipped with the app.")
  return 0


if __name__ == "__main__":
  sys.exit(main())
