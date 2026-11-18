"""Build a relocatable Windows x86_64 PyMOL bundle."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
import urllib.request
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

RUNTIME_VERSION = "3.11.15"
RUNTIME_URL = (
    "https://releases.astral.sh/github/python-build-standalone/releases/download/"
    "20260718/cpython-3.11.15%2B20260718-x86_64-pc-windows-msvc-"
    "install_only_stripped.tar.gz"
)
RUNTIME_ARCHIVE_SHA256 = (
    "a48c2dbe832319f61aa8557c9900caec70f7fed0cbee391a4c9ff9f98b50222d"
)
RUNTIME_PACKAGES = (
    "numpy==1.26.4",
    "pymol-open-source-whl==3.1.0.4",
    "PyQt5==5.15.11",
    "PyQt5-Qt5==5.15.2",
    "PyQt5_sip==12.17.0",
)
ARCHIVE_NAME = "PyMOL-Open-Source_windows-x86_64.zip"
_REQUIRED_BUNDLE_FILES = {"manifest.json", "launch_pymol.cmd"}
_REQUIRED_BUNDLE_CONTENT = (
    "runtime/python/python.exe",
    "runtime/python/python311.dll",
    "runtime/python/Lib/site-packages/pymol/__init__.py",
    "runtime/python/Lib/site-packages/pymol/_cmd.cp311-win_amd64.pyd",
    "runtime/python/Lib/site-packages/pmg_qt/pymol_qt_gui.py",
    "runtime/python/Lib/site-packages/pymol/base.css",
    "runtime/python/Lib/site-packages/pymol/startup_wrapper.py",
    "runtime/python/Lib/site-packages/pymol/data/pymol/icons/alt_logo.png",
    "runtime/python/Lib/site-packages/pymol/data/pymol/splash.png",
    "runtime/python/Lib/site-packages/PyQt5/Qt5/bin/Qt5Core.dll",
    "runtime/python/Lib/site-packages/PyQt5/Qt5/bin/Qt5Gui.dll",
    "runtime/python/Lib/site-packages/PyQt5/Qt5/bin/Qt5Widgets.dll",
)
_CX_FREEZE_MARKERS = {"library.zip", "open-source-pymol.exe", "cx_freeze"}


@dataclass(frozen=True)
class BundleConfig:
    """Paths and identity used by one bundle build."""

    root: Path
    output: Path
    lockfile: Path
    runtime_version: str = RUNTIME_VERSION


def _sha256(path: Path) -> str:
    """Compute the SHA-256 digest of a file.

    Args:
        path: File to hash.

    Returns:
        Lowercase hexadecimal digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def runtime_url(version: str) -> str:
    """Return the approved CPython archive URL or reject another version.

    Args:
        version: Requested CPython version.

    Returns:
        Approved runtime archive URL.
    """
    if version != RUNTIME_VERSION:
        raise ValueError(f"Only CPython {RUNTIME_VERSION} is approved")
    return RUNTIME_URL


def _download_runtime_archive(version: str, destination: Path) -> str:
    """Download and verify the approved runtime archive.

    Args:
        version: Approved CPython version.
        destination: Destination archive path.

    Returns:
        SHA-256 digest of the downloaded archive.
    """
    request = urllib.request.Request(
        runtime_url(version), headers={"User-Agent": "pymol-open-source-bundler"}
    )
    with (
        urllib.request.urlopen(request) as response,
        destination.open("wb") as archive,
    ):
        shutil.copyfileobj(response, archive)
    archive_hash = _sha256(destination)
    if archive_hash != RUNTIME_ARCHIVE_SHA256:
        raise RuntimeError(
            "Downloaded CPython archive SHA-256 does not match the approved hash"
        )
    return archive_hash


def _extract_runtime_archive(archive: Path, runtime: Path) -> None:
    """Extract the already-verified runtime archive into the bundle.

    Args:
        archive: Verified runtime archive.
        runtime: Runtime extraction directory.
    """
    runtime.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        for member in members:
            target = (runtime / member.name).resolve()
            if not target.is_relative_to(runtime.resolve()):
                raise RuntimeError("Runtime archive contains an unsafe path")
            if not member.isdir() and not member.isfile():
                raise RuntimeError("Runtime archive contains a non-regular member")
        for member in members:
            source.extract(member, runtime)


def _provenance(root: Path) -> tuple[str, str]:
    """Return provenance for a clean worktree with an authoritative HEAD.

    Args:
        root: Repository root.

    Returns:
        Git commit and reproducible build timestamp.
    """
    try:
        status = subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ],
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Git worktree provenance is required") from exc
    if status.strip():
        raise RuntimeError(
            "Git worktree must be clean for a release/bundle build: "
            + status.strip()
        )
    try:
        repository_commit = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Git commit provenance is required") from exc
    if not repository_commit:
        raise RuntimeError("Git commit provenance is required")
    override = os.environ.get("GIT_COMMIT")
    if override and override != repository_commit:
        raise RuntimeError("GIT_COMMIT conflicts with repository HEAD")
    git_commit = repository_commit
    source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if source_date_epoch is not None:
        timestamp = _timestamp_from_source_date_epoch(source_date_epoch)
    else:
        timestamp = _commit_timestamp(root)
    return git_commit, timestamp


def _timestamp_from_source_date_epoch(value: str) -> str:
    """Convert a reproducible-build epoch to an ISO timestamp.

    Args:
        value: Non-negative decimal epoch string.

    Returns:
        ISO-8601 timestamp.
    """
    value = value.strip()
    if not value.isdigit():
        raise RuntimeError("SOURCE_DATE_EPOCH must be a non-negative integer")
    try:
        return datetime.fromtimestamp(int(value), UTC).isoformat()
    except (OverflowError, OSError, ValueError) as exc:
        raise RuntimeError("SOURCE_DATE_EPOCH is outside the supported range") from exc


def _commit_timestamp(root: Path) -> str:
    """Return the authoritative ISO timestamp recorded on Git HEAD.

    Args:
        root: Repository root.

    Returns:
        Commit timestamp including timezone.
    """
    try:
        timestamp = subprocess.check_output(
            ["git", "-C", str(root), "show", "-s", "--format=%cI", "HEAD"],
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Git commit timestamp provenance is required") from exc
    if not timestamp:
        raise RuntimeError("Git commit timestamp provenance is required")
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise RuntimeError("Git commit timestamp provenance is invalid") from exc
    if parsed.tzinfo is None:
        raise RuntimeError("Git commit timestamp provenance must include a timezone")
    return timestamp


def overlay_inventory(root: Path) -> dict[Path, Path]:
    """Return repository overlays and their bundle targets.

    Args:
        root: Repository root.

    Returns:
        Mapping from overlay source paths to bundle-relative targets.
    """
    return {
        root / "edited/pmg_qt/pymol_qt_gui.py": Path(
            "runtime/python/Lib/site-packages/pmg_qt/pymol_qt_gui.py"
        ),
        root / "edited/pymol/data/pymol/base.css": Path(
            "runtime/python/Lib/site-packages/pymol/base.css"
        ),
        root / "edited/pymol/__init__.py": Path(
            "runtime/python/Lib/site-packages/pymol/__init__.py"
        ),
        root / "edited/pymol/startup_wrapper.py": Path(
            "runtime/python/Lib/site-packages/pymol/startup_wrapper.py"
        ),
        root / "alternative_design/alt_logo.png": Path(
            "runtime/python/Lib/site-packages/pymol/data/pymol/icons/alt_logo.png"
        ),
        root / "os_specific/windows/splash.png": Path(
            "runtime/python/Lib/site-packages/pymol/data/pymol/splash.png"
        ),
    }


def _find_python(runtime: Path) -> Path:
    """Find the shortest-path Python executable in a runtime tree.

    Args:
        runtime: Extracted runtime directory.

    Returns:
        Python executable path.
    """
    candidates = sorted(runtime.rglob("python.exe"))
    if not candidates:
        raise FileNotFoundError("Standalone runtime did not contain python.exe")
    return min(candidates, key=lambda candidate: len(candidate.parts))


def _run(args: Iterable[str], cwd: Path) -> None:
    """Run a checked subprocess in a working directory.

    Args:
        args: Executable and argument sequence.
        cwd: Subprocess working directory.
    """
    subprocess.run(list(args), check=True, cwd=cwd)


def _write_launcher(output: Path, python_exe: Path) -> None:
    """Write the relative launcher used by the bundle.

    Args:
        output: Bundle output directory.
        python_exe: Runtime Python executable.
    """
    runtime_path = python_exe.relative_to(output).as_posix().replace("/", "\\")
    (output / "launch_pymol.cmd").write_text(
        "@echo off\r\n"
        'set "PYTHONPATH="\r\n'
        'set "PYTHONHOME="\r\n'
        'set "PYTHONNOUSERSITE=1"\r\n'
        'set "BUNDLE=%~dp0"\r\n'
        f'"%BUNDLE%{runtime_path}" -m pymol %*\r\n',
        encoding="utf-8",
    )


def _write_manifest(
    config: BundleConfig,
    python_exe: Path,
    runtime_archive_sha256: str,
    git_commit: str,
    timestamp: str,
) -> None:
    """Write bundle dependency and provenance metadata.

    Args:
        config: Bundle build configuration.
        python_exe: Runtime Python executable.
        runtime_archive_sha256: Verified runtime archive digest.
        git_commit: Authoritative source commit.
        timestamp: Reproducible build timestamp.
    """
    lock_hash = _sha256(config.lockfile)
    lock = tomllib.loads(config.lockfile.read_text(encoding="utf-8"))
    dependency_sources = _locked_dependency_sources(lock)
    manifest = {
        "target": "windows-x86_64",
        "runtime": {
            "version": config.runtime_version,
            "source_url": runtime_url(config.runtime_version),
            "sha256": runtime_archive_sha256,
        },
        "dependencies": list(RUNTIME_PACKAGES),
        "dependency_sources": dependency_sources,
        "lock_sha256": lock_hash,
        "git_commit": git_commit,
        "timestamp": timestamp,
    }
    ci_metadata = {
        "GITHUB_SHA": os.environ["GITHUB_SHA"]
    } if "GITHUB_SHA" in os.environ else {}
    if ci_metadata:
        manifest["ci"] = ci_metadata
    (config.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _valid_hash(value: object) -> bool:
    """Return whether a manifest value is a SHA-256 digest.

    Args:
        value: Candidate manifest value.

    Returns:
        Whether the value is a valid hexadecimal SHA-256 digest.
    """
    if not isinstance(value, str):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(
        character in "0123456789abcdef" for character in digest.lower()
    )


def _locked_dependency_sources(lock: dict) -> dict[str, list[dict[str, str]]]:
    """Return locked artifacts for approved runtime dependencies.

    Args:
        lock: Decoded lockfile contents.

    Returns:
        Mapping from package names to locked artifact metadata.
    """
    package_names = {
        package.split("==", 1)[0].lower().replace("_", "-")
        for package in RUNTIME_PACKAGES
    }
    requested_versions = {
        package.split("==", 1)[0].lower().replace("_", "-"): package.split("==", 1)[1]
        for package in RUNTIME_PACKAGES
    }
    dependency_sources = {}
    for package in lock.get("package", []):
        normalized_name = package["name"].lower().replace("_", "-")
        if normalized_name not in package_names:
            continue
        if package.get("version") != requested_versions[normalized_name]:
            raise RuntimeError("Locked dependency version does not match approval")
        artifacts = []
        for key in ("sdist", "wheels"):
            entries = package.get(key, [])
            if isinstance(entries, dict):
                entries = [entries]
            artifacts.extend(
                {"url": item["url"], "sha256": item["hash"]} for item in entries
            )
        dependency_sources[package["name"]] = artifacts
    missing_sources = package_names - {
        name.lower().replace("_", "-") for name in dependency_sources
    }
    if missing_sources or any(
        not all(item.get("url") and item.get("sha256") for item in artifacts)
        for artifacts in dependency_sources.values()
    ):
        raise RuntimeError("Locked dependency URL/hash provenance is incomplete")
    return dependency_sources


def _invalidate_output(path: Path) -> None:
    """Remove prior output so failed packaging cannot look successful.

    Args:
        path: Output path to remove.
    """
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _validate_bundle(bundle: Path, config: BundleConfig | None = None) -> None:
    """Validate that ``bundle`` has the approved self-contained shape.

    Args:
        bundle: Bundle directory to validate.
        config: Optional build configuration supplying provenance paths.
    """
    if not bundle.is_dir():
        raise FileNotFoundError(f"Windows x86_64 bundle is missing: {bundle}")
    missing = [
        name
        for name in sorted(_REQUIRED_BUNDLE_FILES)
        if not (bundle / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            f"Bundle is missing required files: {', '.join(missing)}"
        )
    missing_content = [relative for relative in _REQUIRED_BUNDLE_CONTENT
                       if not (bundle / relative).is_file()]
    if missing_content:
        raise RuntimeError(
            "Bundle is incomplete; missing required content: "
            + ", ".join(missing_content)
        )
    try:
        manifest = json.loads(
            (bundle / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Bundle manifest.json is not valid JSON") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("Bundle manifest.json must contain an object")
    if manifest.get("target") != "windows-x86_64":
        raise RuntimeError("Bundle manifest target is not windows-x86_64")
    runtime_provenance = manifest.get("runtime")
    if not isinstance(runtime_provenance, dict):
        raise RuntimeError("Bundle manifest runtime provenance is incomplete")
    if config is None:
        root = Path(__file__).resolve().parents[2]
        config = BundleConfig(root, bundle, root / "uv.lock")
    if runtime_provenance.get("version") != config.runtime_version:
        raise RuntimeError("Bundle manifest runtime provenance is incomplete")
    if runtime_provenance.get("source_url") != runtime_url(config.runtime_version):
        raise RuntimeError("Bundle manifest runtime provenance is incomplete")
    if runtime_provenance.get("sha256") != RUNTIME_ARCHIVE_SHA256:
        raise RuntimeError("Bundle manifest runtime hash does not match approval")
    if manifest.get("lock_sha256") != _sha256(config.lockfile):
        raise RuntimeError("Bundle manifest lock provenance is incomplete")
    try:
        authoritative_commit = subprocess.check_output(
            ["git", "-C", str(config.root), "rev-parse", "HEAD"],
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Git commit provenance is required") from exc
    if manifest.get("git_commit") != authoritative_commit:
        raise RuntimeError("Bundle manifest Git commit is stale")
    timestamp = manifest.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp:
        raise RuntimeError("Bundle manifest build provenance is incomplete")
    source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if source_date_epoch is not None:
        expected_timestamp = _timestamp_from_source_date_epoch(source_date_epoch)
    else:
        expected_timestamp = _commit_timestamp(config.root)
    if timestamp != expected_timestamp:
        raise RuntimeError("Bundle manifest timestamp is stale")
    dependencies = {
        package.split("==", 1)[0].lower().replace("_", "-")
        for package in RUNTIME_PACKAGES
    }
    manifest_dependencies = manifest.get("dependencies")
    if not isinstance(manifest_dependencies, list):
        raise RuntimeError("Bundle manifest dependency list is incomplete")
    if manifest_dependencies != list(RUNTIME_PACKAGES) or {
        package.split("==", 1)[0].lower().replace("_", "-")
        for package in manifest_dependencies
    } != dependencies:
        raise RuntimeError("Bundle manifest dependency list is incomplete")
    sources = manifest.get("dependency_sources", {})
    if not isinstance(sources, dict):
        raise RuntimeError("Bundle manifest dependency provenance is incomplete")
    lock = tomllib.loads(config.lockfile.read_text(encoding="utf-8"))
    if sources != _locked_dependency_sources(lock) or {
        name.lower().replace("_", "-") for name in sources
    } != dependencies or any(
        not artifacts
        or any(
            not item.get("url") or not _valid_hash(item.get("sha256"))
            for item in artifacts
        )
        for artifacts in sources.values()
    ):
        raise RuntimeError("Bundle manifest dependency provenance is incomplete")

    bundle_root = bundle.resolve()
    for path in sorted(bundle.rglob("*")):
        relative = path.relative_to(bundle).as_posix()
        if relative.startswith("Lib/site-packages/"):
            raise RuntimeError(
                f"Bundle contains a root-level overlay: {relative}"
            )
        if path.is_symlink():
            raise RuntimeError(f"Bundle contains an unsafe symlink: {relative}")
        if not path.resolve().is_relative_to(bundle_root):
            raise RuntimeError(f"Bundle contains an unsafe path: {relative}")
        lowered_name = path.name.lower()
        if lowered_name.startswith("vc_redist") and lowered_name.endswith(".exe"):
            raise RuntimeError(f"Bundle contains a VC redistributable: {relative}")
        if lowered_name in _CX_FREEZE_MARKERS:
            raise RuntimeError(
                f"Bundle contains a cx_Freeze output marker: {relative}"
            )


def create_deterministic_archive(
    bundle: Path, archive: Path, config: BundleConfig | None = None
) -> None:
    """Create a byte-stable ZIP archive from a validated bundle.

    Args:
        bundle: Validated bundle directory.
        archive: Destination ZIP path.
        config: Optional build configuration supplying provenance paths.
    """
    _invalidate_output(archive)
    _validate_bundle(bundle, config)
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive.with_suffix(archive.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as destination:
            for source in sorted(bundle.rglob("*")):
                if not source.is_file():
                    continue
                relative = source.relative_to(bundle).as_posix()
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 0
                info.external_attr = 0
                destination.writestr(info, source.read_bytes())
        temporary.replace(archive)
    finally:
        if temporary.exists():
            temporary.unlink()


def prepare_inno_staging(
    bundle: Path,
    staging: Path,
    logo: Path,
    config: BundleConfig | None = None,
) -> None:
    """Stage the validated bundle and installer asset for the x64 script.

    Args:
        bundle: Validated bundle directory.
        staging: Installer staging directory.
        logo: Inno Setup logo path.
        config: Optional build configuration supplying provenance paths.
    """
    _invalidate_output(staging)
    _validate_bundle(bundle, config)
    if not logo.is_file():
        raise FileNotFoundError(f"Inno Setup logo is missing: {logo}")
    temporary = staging.with_name(staging.name + ".tmp")
    _invalidate_output(temporary)
    try:
        sources = temporary / "inno-sources"
        assets = temporary / "inno-assets"
        sources.mkdir(parents=True)
        assets.mkdir()
        for source in sorted(bundle.rglob("*")):
            relative = source.relative_to(bundle)
            target = sources / relative
            if source.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        shutil.copy2(logo, assets / "logo.ico")
        temporary.replace(staging)
    finally:
        _invalidate_output(temporary)


def _copy_overlays(root: Path, output: Path) -> None:
    """Copy every approved overlay and fail on a missing source.

    Args:
        root: Repository root.
        output: Bundle output directory.
    """
    for source, relative_target in overlay_inventory(root).items():
        if not source.is_file():
            raise FileNotFoundError(f"Missing required overlay: {source}")
        target = output / relative_target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def build(config: BundleConfig) -> None:
    """Build a bundle and remove output if any prerequisite fails.

    Args:
        config: Bundle build configuration.
    """
    _invalidate_output(config.output)
    try:
        _build(config)
    except BaseException:
        _invalidate_output(config.output)
        raise


def _build(config: BundleConfig) -> None:
    """Assemble the offline bundle using uv and the committed lockfile.

    Args:
        config: Bundle build configuration.
    """
    if platform.system() != "Windows" or platform.machine().lower() not in {
        "amd64",
        "x86_64",
    }:
        raise RuntimeError("Windows x86_64 is the only supported bundle target")
    uv = shutil.which("uv")
    if uv is None:
        raise FileNotFoundError("uv is required to build the standalone bundle")
    git_commit, timestamp = _provenance(config.root)
    config.output.mkdir(parents=True)
    runtime = config.output / "runtime"
    with tempfile.TemporaryDirectory() as temporary_directory:
        archive = Path(temporary_directory) / "python-runtime.tar.gz"
        runtime_archive_sha256 = _download_runtime_archive(
            config.runtime_version, archive
        )
        _extract_runtime_archive(archive, runtime)
    python_exe = _find_python(runtime)
    with tempfile.TemporaryDirectory() as temporary_directory:
        exported = Path(temporary_directory) / "requirements.txt"
        _run(
            [
                uv,
                "export",
                "--locked",
                "--no-emit-project",
                "--format",
                "requirements.txt",
                "--output-file",
                str(exported),
            ],
            config.root,
        )
        _run(
            [
                uv,
                "pip",
                "sync",
                "--system",
                "--break-system-packages",
                "--python",
                str(python_exe),
                "--only-binary=:all:",
                "--require-hashes",
                str(exported),
            ],
            config.root,
        )
    _copy_overlays(config.root, config.output)
    _write_launcher(config.output, python_exe)
    _write_manifest(config, python_exe, runtime_archive_sha256, git_commit, timestamp)
