"""The installed checker's record of its own files: ``MANIFEST.json``.

``opp-workflow style-install`` writes the manifest beside ``check.py`` when it
copies the checker into a repository's ``.opp/style/``: the plugin's version
and each file's SHA-256. The checker verifies it before every run, so a copy
edited by hand cannot judge a push check; ``style-install`` uses the same
functions to refuse to overwrite such a copy. Every line ending is hashed as
LF, so a checkout with ``core.autocrlf`` matches the plugin's files.

The check catches a rule loosened by hand, not deliberate tampering: a copy
whose files and manifest are edited together, or a compiled cache planted
beside them, still runs.
"""

from __future__ import annotations

import hashlib
import json
import os

NAME = "MANIFEST.json"
"""The manifest's file name, beside ``check.py``."""

CLUTTER = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})
"""Files an operating system drops into any folder, which are neither hashed nor counted."""


class ManifestError(Exception):
    """The manifest exists but cannot be read as one."""


def file_hash(path: str) -> str:
    """Hash one file, line endings normalised.

    Args:
        path: The file.

    Returns:
        ``sha256:`` and the SHA-256 of its bytes with CRLF read as LF, in
        hexadecimal. The prefix keeps a secrets scanner from taking the
        digest for a high-entropy key.
    """
    with open(path, "rb") as tmp_file:
        return "sha256:" + hashlib.sha256(tmp_file.read().replace(b"\r\n", b"\n")).hexdigest()


def files(folder: str) -> dict[str, str]:
    """Hash every file of a checker folder but the manifest and compiled caches.

    Args:
        folder: The folder that holds ``check.py``.

    Returns:
        Each file's path relative to the folder, with forward slashes,
        mapped to its hash; compiled caches and :data:`CLUTTER` are left
        out, and the result is empty when the folder does not exist.
    """
    tmp_files = {}
    for tmp_current, tmp_subfolders, tmp_names in os.walk(folder):
        tmp_subfolders[:] = sorted(tmp_name for tmp_name in tmp_subfolders if tmp_name != "__pycache__")
        for tmp_name in sorted(tmp_names):
            if tmp_name.endswith(".pyc") or tmp_name in CLUTTER:
                continue
            tmp_path = os.path.join(tmp_current, tmp_name)
            tmp_relative = os.path.relpath(tmp_path, folder).replace(os.sep, "/")
            if tmp_relative != NAME:
                tmp_files[tmp_relative] = file_hash(tmp_path)
    return tmp_files


def read(folder: str) -> dict | None:
    """Read a checker folder's manifest.

    Args:
        folder: The folder that holds ``check.py``.

    Returns:
        The manifest, or None when the folder has none.

    Raises:
        ManifestError: The manifest exists but is not JSON or lists no files.
    """
    try:
        with open(os.path.join(folder, NAME), encoding="utf-8") as tmp_file:
            tmp_manifest = json.load(tmp_file)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exception:
        raise ManifestError(f"{NAME} cannot be read: {exception}") from exception
    tmp_files = tmp_manifest.get("files") if isinstance(tmp_manifest, dict) else None
    if not isinstance(tmp_files, dict) or not all(isinstance(tmp_value, str) for tmp_value in tmp_files.values()):
        raise ManifestError(f"{NAME} lists no files")
    return tmp_manifest


def edited(folder: str, manifest: dict | None) -> list[str]:
    """Find the files of a checker folder that differ from its manifest.

    Args:
        folder: The folder that holds ``check.py``.
        manifest: Its manifest, or None when it has none.

    Returns:
        The edited, missing and unlisted files, relative to the folder,
        sorted.
    """
    # A manifest written before the digests carried their prefix still counts.
    tmp_recorded = {
        tmp_name: tmp_value if tmp_value.startswith("sha256:") else "sha256:" + tmp_value
        for tmp_name, tmp_value in (manifest["files"] if manifest else {}).items()
    }
    tmp_present = files(folder)
    tmp_names = set(tmp_recorded) | set(tmp_present)
    return sorted(tmp_name for tmp_name in tmp_names if tmp_recorded.get(tmp_name) != tmp_present.get(tmp_name))
