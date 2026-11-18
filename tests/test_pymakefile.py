"""Tests for the pymake tasks and Windows bundle helpers."""

import io
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import pymakefile
from scripts.python import windows_bundle


def _make_valid_bundle(root: Path) -> Path:
  """Create the minimum build-produced bundle shape for packaging tests.

  Args:
    root: Temporary directory receiving the bundle.

  Returns:
    Path to the valid test bundle.
  """
  bundle = root / "bundle"
  for relative in windows_bundle._REQUIRED_BUNDLE_CONTENT:
    path = bundle / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"bundle-content")
  lockfile = pymakefile._PROJECT_ROOT / "uv.lock"
  lock = tomllib.loads(lockfile.read_text(encoding="utf-8"))
  dependencies = list(windows_bundle.RUNTIME_PACKAGES)
  manifest = {
      "target": "windows-x86_64",
      "runtime": {
          "version": windows_bundle.RUNTIME_VERSION,
          "source_url": windows_bundle.runtime_url(windows_bundle.RUNTIME_VERSION),
          "sha256": windows_bundle.RUNTIME_ARCHIVE_SHA256,
      },
      "dependencies": dependencies,
      "dependency_sources": windows_bundle._locked_dependency_sources(lock),
      "lock_sha256": windows_bundle._sha256(lockfile),
      "git_commit": pymakefile.run(
          "git rev-parse HEAD", capture=True, cwd=pymakefile._PROJECT_ROOT
      ),
      "timestamp": windows_bundle._commit_timestamp(pymakefile._PROJECT_ROOT),
  }
  (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
  (bundle / "launch_pymol.cmd").write_text("launch", encoding="utf-8")
  return bundle


class PymakeBuildTaskTest(unittest.TestCase):
  """Verify task dispatch, bundling, and packaging behavior."""

  def test_runtime_url_rejects_unapproved_version(self) -> None:
    """Reject runtime versions outside the approved version."""
    self.assertIn("3.11.15", windows_bundle.runtime_url("3.11.15"))
    with self.assertRaises(ValueError):
      windows_bundle.runtime_url("3.12.0")

  def test_runtime_archive_hashes_downloaded_bytes(self) -> None:
    """Hash downloaded runtime bytes before accepting the archive."""
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(b"archive")
    with tempfile.TemporaryDirectory() as temporary_directory:
      destination = Path(temporary_directory) / "python.zip"
      expected_hash = hashlib.sha256(b"archive").hexdigest()
      with mock.patch(
          "scripts.python.windows_bundle.urllib.request.urlopen",
          return_value=response,
      ) as urlopen, mock.patch.object(
          windows_bundle, "RUNTIME_ARCHIVE_SHA256", expected_hash
      ):
        archive_hash = windows_bundle._download_runtime_archive(
            "3.11.15", destination
        )
    request = urlopen.call_args.args[0]
    self.assertEqual(request.full_url, windows_bundle.runtime_url("3.11.15"))
    self.assertEqual(
        archive_hash,
        expected_hash,
    )

  def test_changed_runtime_archive_fails_verification(self) -> None:
    """Reject an archive whose bytes do not match the approved hash."""
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(b"changed")
    with tempfile.TemporaryDirectory() as temporary_directory:
      with mock.patch(
          "scripts.python.windows_bundle.urllib.request.urlopen",
          return_value=response,
      ):
        with self.assertRaises(RuntimeError):
          windows_bundle._download_runtime_archive(
              "3.11.15", Path(temporary_directory) / "python.tar.gz"
          )

  def test_verified_archive_content_becomes_installed_runtime(self) -> None:
    """Extract verified archive members into the runtime directory."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      source = root / "python.exe"
      source.write_bytes(b"verified-runtime")
      archive = root / "runtime.tar.gz"
      with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(source, arcname="python/python.exe")
      runtime = root / "installed"
      windows_bundle._extract_runtime_archive(archive, runtime)
      self.assertEqual(
          (runtime / "python/python.exe").read_bytes(), b"verified-runtime"
      )

  def test_runtime_archive_rejects_links(self) -> None:
    """Reject symbolic and hard links in runtime archives."""
    for member_type in (tarfile.SYMTYPE, tarfile.LNKTYPE):
      with self.subTest(member_type=member_type), tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        archive = root / "runtime.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
          member = tarfile.TarInfo("python/link")
          member.type = member_type
          member.linkname = "../../outside"
          bundle.addfile(member)
        with self.assertRaises(RuntimeError):
          windows_bundle._extract_runtime_archive(archive, root / "installed")

  def test_manifest_records_archive_and_required_provenance(self) -> None:
    """Record archive, Git, timestamp, and dependency provenance."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      lockfile = pymakefile._PROJECT_ROOT / "uv.lock"
      output = root / "bundle"
      output.mkdir()
      python_exe = output / "python.exe"
      python_exe.write_bytes(b"python")
      config = windows_bundle.BundleConfig(root, output, lockfile)
      windows_bundle._write_manifest(
          config, python_exe, "archive-hash", "commit", "timestamp"
      )
      manifest = json.loads((output / "manifest.json").read_text())
    self.assertEqual(manifest["runtime"]["sha256"], "archive-hash")
    self.assertEqual(manifest["git_commit"], "commit")
    self.assertEqual(manifest["timestamp"], "timestamp")
    self.assertEqual(
        set(manifest["dependency_sources"]),
        {"numpy", "pymol-open-source-whl", "pyqt5", "pyqt5-qt5", "pyqt5-sip"},
    )
    self.assertTrue(
        all(
            item["url"].startswith("https://") and item["sha256"]
            for artifacts in manifest["dependency_sources"].values()
            for item in artifacts
      )
    )

  def test_volatile_ci_metadata_does_not_change_archive_bytes(self) -> None:
    """Keep archive bytes stable when volatile CI metadata changes."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      bundle = _make_valid_bundle(root)
      lockfile = pymakefile._PROJECT_ROOT / "uv.lock"
      config = windows_bundle.BundleConfig(root, bundle, lockfile)
      git_commit = pymakefile.run(
          "git rev-parse HEAD", capture=True, cwd=pymakefile._PROJECT_ROOT
      )
      timestamp = windows_bundle._commit_timestamp(pymakefile._PROJECT_ROOT)
      with mock.patch.dict(
          "os.environ",
          {"GITHUB_SHA": git_commit, "GITHUB_RUN_ID": "run-one"},
          clear=False,
      ):
        windows_bundle._write_manifest(
            config,
            bundle / "runtime/python/python.exe",
            windows_bundle.RUNTIME_ARCHIVE_SHA256,
            git_commit,
            timestamp,
        )
        windows_bundle.create_deterministic_archive(bundle, root / "first.zip")
      first_manifest = json.loads(
          (bundle / "manifest.json").read_text(encoding="utf-8")
      )
      with mock.patch.dict(
          "os.environ",
          {"GITHUB_SHA": git_commit, "GITHUB_RUN_ID": "run-two"},
          clear=False,
      ):
        windows_bundle._write_manifest(
            config,
            bundle / "runtime/python/python.exe",
            windows_bundle.RUNTIME_ARCHIVE_SHA256,
            git_commit,
            timestamp,
        )
        windows_bundle.create_deterministic_archive(bundle, root / "second.zip")
      second_manifest = json.loads(
          (bundle / "manifest.json").read_text(encoding="utf-8")
      )
      first_archive = (root / "first.zip").read_bytes()
      second_archive = (root / "second.zip").read_bytes()
    self.assertEqual(first_manifest, second_manifest)
    self.assertNotIn("GITHUB_RUN_ID", second_manifest.get("ci", {}))
    self.assertEqual(first_archive, second_archive)

  def test_provenance_fails_when_git_is_unavailable(self) -> None:
    """Reject builds when Git provenance cannot be read."""
    with mock.patch.dict("os.environ", {}, clear=True), mock.patch(
        "scripts.python.windows_bundle.subprocess.check_output",
        side_effect=FileNotFoundError,
    ):
      with self.assertRaises(RuntimeError):
        windows_bundle._provenance(Path("root"))

  def test_provenance_accepts_clean_worktree(self) -> None:
    """Accept provenance from a clean worktree."""
    with mock.patch.object(
        windows_bundle.subprocess,
        "check_output",
        side_effect=["", "head\n", "2026-08-09T00:00:00+00:00\n"],
    ):
      commit, _ = windows_bundle._provenance(Path("root"))
    self.assertEqual(commit, "head")

  def test_provenance_is_stable_and_honors_source_date_epoch(self) -> None:
    """Produce stable provenance and honor the source-date epoch."""
    with mock.patch.object(
        windows_bundle.subprocess,
        "check_output",
        side_effect=[
            "",
            "head\n",
            "2026-08-09T00:00:00+00:00\n",
            "",
            "head\n",
            "2026-08-09T00:00:00+00:00\n",
        ],
    ):
      first = windows_bundle._provenance(Path("root"))
      second = windows_bundle._provenance(Path("root"))
    self.assertEqual(first, second)

    with mock.patch.dict("os.environ", {"SOURCE_DATE_EPOCH": "1786233600"}, clear=True), mock.patch.object(
        windows_bundle.subprocess,
        "check_output",
        side_effect=["", "head\n"],
    ):
      _, timestamp = windows_bundle._provenance(Path("root"))
    self.assertEqual(timestamp, "2026-08-09T00:00:00+00:00")

  def test_provenance_rejects_invalid_source_date_epoch(self) -> None:
    """Reject malformed source-date epoch values."""
    with mock.patch.dict("os.environ", {"SOURCE_DATE_EPOCH": "not-an-epoch"}, clear=True), mock.patch.object(
        windows_bundle.subprocess,
        "check_output",
        side_effect=["", "head\n"],
    ):
      with self.assertRaisesRegex(RuntimeError, "SOURCE_DATE_EPOCH"):
        windows_bundle._provenance(Path("root"))

  def test_provenance_rejects_dirty_tracked_worktree(self) -> None:
    """Reject a worktree containing tracked changes."""
    with mock.patch.object(
        windows_bundle.subprocess,
        "check_output",
        return_value=" M tracked.py\n",
    ) as check_output:
      with self.assertRaisesRegex(RuntimeError, "worktree must be clean"):
        windows_bundle._provenance(Path("root"))
    self.assertEqual(check_output.call_count, 1)

  def test_provenance_rejects_untracked_worktree(self) -> None:
    """Reject a worktree containing untracked files."""
    with mock.patch.object(
        windows_bundle.subprocess,
        "check_output",
        return_value="?? untracked.txt\n",
    ):
      with self.assertRaisesRegex(RuntimeError, "worktree must be clean"):
        windows_bundle._provenance(Path("root"))

  def test_provenance_accepts_matching_override(self) -> None:
    """Accept a Git commit override matching HEAD."""
    with mock.patch.dict("os.environ", {"GIT_COMMIT": "head"}, clear=True), mock.patch(
        "scripts.python.windows_bundle.subprocess.check_output",
        side_effect=["", "head\n", "2026-08-09T00:00:00+00:00\n"],
    ):
      commit, _ = windows_bundle._provenance(Path("root"))
    self.assertEqual(commit, "head")

  def test_provenance_rejects_conflicting_override(self) -> None:
    """Reject a Git commit override that conflicts with HEAD."""
    with mock.patch.dict("os.environ", {"GIT_COMMIT": "stale"}, clear=True), mock.patch(
        "scripts.python.windows_bundle.subprocess.check_output",
        side_effect=["", "head\n"],
    ):
      with self.assertRaises(RuntimeError):
        windows_bundle._provenance(Path("root"))

  def test_build_removes_stale_output_when_uv_is_missing(self) -> None:
    """Remove stale output when uv is unavailable."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      output = root / "bundle"
      output.mkdir()
      (output / "manifest.json").write_text("stale")
      config = windows_bundle.BundleConfig(root, output, root / "uv.lock")
      with mock.patch.object(windows_bundle.platform, "system", return_value="Windows"), \
          mock.patch.object(windows_bundle.platform, "machine", return_value="AMD64"), \
          mock.patch.object(windows_bundle.shutil, "which", return_value=None):
        with self.assertRaises(FileNotFoundError):
          windows_bundle.build(config)
      self.assertFalse(output.exists())

  def test_build_removes_output_when_runtime_download_fails(self) -> None:
    """Remove output when runtime download fails."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      output = root / "bundle"
      output.mkdir()
      (output / "manifest.json").write_text("stale")
      config = windows_bundle.BundleConfig(root, output, root / "uv.lock")
      with mock.patch.object(windows_bundle.platform, "system", return_value="Windows"), \
          mock.patch.object(windows_bundle.platform, "machine", return_value="AMD64"), \
          mock.patch.object(windows_bundle.shutil, "which", return_value="uv"), \
          mock.patch.object(windows_bundle, "_download_runtime_archive", side_effect=RuntimeError("download failed")):
        with self.assertRaises(RuntimeError):
          windows_bundle.build(config)
      self.assertFalse(output.exists())

  def test_runtime_discovery_prefers_top_level_interpreter(self) -> None:
    """Prefer the shortest-path runtime interpreter."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      runtime = Path(temporary_directory)
      top_level = runtime / "python.exe"
      nested = runtime / "Lib/venv/scripts/nt/python.exe"
      nested.parent.mkdir(parents=True)
      top_level.write_bytes(b"")
      nested.write_bytes(b"")
      self.assertEqual(windows_bundle._find_python(runtime), top_level)

  def test_missing_overlay_fails_before_copy(self) -> None:
    """Fail before copying when an overlay source is missing."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      output = root / "bundle"
      output.mkdir()
      with self.assertRaises(FileNotFoundError):
        windows_bundle._copy_overlays(root, output)

  def test_build_sequences_runtime_dependencies_overlays_and_manifest(self) -> None:
    """Build runtime, dependencies, overlays, launcher, and manifest in order."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      output = root / "bundle"
      lockfile = root / "uv.lock"
      lockfile.write_text('lock-version = "1"\n', encoding="utf-8")
      config = windows_bundle.BundleConfig(root, output, lockfile)
      python_exe = output / "runtime/python.exe"
      calls = []
      run_commands = []

      def record_run(args, cwd, **kwargs):
        calls.append("run")
        run_commands.append(args)

      with mock.patch.object(windows_bundle.platform, "system", return_value="Windows"), \
          mock.patch.object(windows_bundle.platform, "machine", return_value="AMD64"), \
          mock.patch.object(windows_bundle.shutil, "which", return_value="uv"), \
          mock.patch.object(windows_bundle, "_download_runtime_archive", return_value="archive"), \
          mock.patch.object(windows_bundle, "_extract_runtime_archive", side_effect=lambda *args: calls.append("extract")), \
          mock.patch.object(windows_bundle, "_run", side_effect=record_run), \
          mock.patch.object(windows_bundle, "_find_python", return_value=python_exe), \
          mock.patch.object(windows_bundle, "_copy_overlays", side_effect=lambda *args: calls.append("overlays")), \
          mock.patch.object(windows_bundle, "_provenance", return_value=("commit", "timestamp")), \
          mock.patch.object(windows_bundle, "_write_launcher", side_effect=lambda *args: calls.append("launcher")), \
          mock.patch.object(windows_bundle, "_write_manifest", side_effect=lambda *args: calls.append("manifest")):
        windows_bundle.build(config)

    self.assertEqual(
        calls, ["extract", "run", "run", "overlays", "launcher", "manifest"]
    )
    export_command = next(
        command for command in run_commands if command[1:2] == ["export"]
    )
    self.assertEqual(export_command[:3], ["uv", "export", "--locked"])
    sync_command = next(
        command for command in run_commands if command[1:3] == ["pip", "sync"]
    )
    self.assertIn("--only-binary=:all:", sync_command)
    self.assertIn("--require-hashes", sync_command)

  def test_windows_bundle_task_delegates_on_windows(self) -> None:
    """Delegate the bundle task to the bundle builder on Windows."""
    with mock.patch.object(
        pymakefile.platform, "system", return_value="Windows"
    ), mock.patch("scripts.python.windows_bundle.build") as build:
      pymakefile.build_windows_bundle()
    build.assert_called_once()

  def test_windows_artifact_task_guards_platform(self) -> None:
    """Reject Windows artifact builds on other platforms."""
    with mock.patch.object(pymakefile.platform, "system", return_value="Linux"):
      with self.assertRaisesRegex(RuntimeError, "only supported on Windows"):
        pymakefile.build_windows_artifacts()

  def test_windows_artifact_task_orders_bundle_zip_and_installer(self) -> None:
    """Build the bundle, ZIP, and installer in the required order."""
    calls = []
    with mock.patch.object(pymakefile.platform, "system", return_value="Windows"), \
        mock.patch.object(pymakefile, "build_windows_bundle", side_effect=lambda: calls.append("bundle")), \
        mock.patch.object(pymakefile, "package_windows_bundle", side_effect=lambda: calls.append("zip")), \
        mock.patch.object(pymakefile, "build_inno_setup", side_effect=lambda architecture: calls.append(architecture)):
      pymakefile.build_windows_artifacts()
    self.assertEqual(calls, ["bundle", "zip", "x64"])

  def test_overlay_inventory_preserves_required_files(self) -> None:
    """Keep all required overlay sources and target locations."""
    inventory = windows_bundle.overlay_inventory(Path("root"))
    self.assertEqual(len(inventory), 6)
    self.assertEqual(
        {path.name for path in inventory},
        {"pymol_qt_gui.py", "base.css", "__init__.py", "startup_wrapper.py", "alt_logo.png", "splash.png"},
    )
    self.assertTrue(
        all(
            target.parts[:4] == ("runtime", "python", "Lib", "site-packages")
            for target in inventory.values()
        )
    )
    self.assertNotIn(Path("Lib/site-packages/pymol/base.css"), inventory.values())

  def test_rebuild_removes_stale_root_level_overlay_output(self) -> None:
    """Remove stale root-level overlays before rebuilding."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      output = root / "bundle"
      stale = output / "Lib/site-packages/pymol/__init__.py"
      stale.parent.mkdir(parents=True)
      stale.write_bytes(b"stale")
      config = windows_bundle.BundleConfig(root, output, root / "uv.lock")

      def assert_clean_output(_config):
        self.assertFalse(stale.exists())
        output.mkdir()

      with mock.patch.object(windows_bundle, "_build", side_effect=assert_clean_output):
        windows_bundle.build(config)

  def test_launcher_is_relative(self) -> None:
    """Write a launcher that uses the bundle-relative runtime path."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      output = Path(temporary_directory)
      windows_bundle._write_launcher(output, output / "runtime/python.exe")
      launcher = (output / "launch_pymol.cmd").read_text(encoding="utf-8")
    self.assertIn("%~dp0", launcher)
    self.assertIn('set "PYTHONPATH="', launcher)
    self.assertIn('set "PYTHONHOME="', launcher)
    self.assertIn('set "PYTHONNOUSERSITE=1"', launcher)
    self.assertNotIn(str(output), launcher)

  def test_archive_is_deterministic_and_contains_bundle_identity(self) -> None:
    """Create identical archives containing the complete bundle."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      bundle = _make_valid_bundle(root)
      first = root / "first.zip"
      second = root / "second.zip"
      windows_bundle.create_deterministic_archive(bundle, first)
      windows_bundle.create_deterministic_archive(bundle, second)
      self.assertEqual(first.read_bytes(), second.read_bytes())
      with zipfile.ZipFile(first) as archive:
        self.assertEqual(
            set(archive.namelist()),
            {
                "launch_pymol.cmd",
                "manifest.json",
                *windows_bundle._REQUIRED_BUNDLE_CONTENT,
            },
        )
        self.assertEqual(
            archive.read("runtime/python/python.exe"), b"bundle-content"
        )

  def test_archive_rejects_installer_and_cx_freeze_contents(self) -> None:
    """Reject installer and cx_Freeze markers in portable archives."""
    for filename in ("VC_redist.x64.exe", "library.zip", "Open-Source-PyMOL.exe"):
      with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temporary_directory:
        bundle = _make_valid_bundle(Path(temporary_directory))
        (bundle / filename).write_bytes(b"unsafe")
        with self.assertRaises(RuntimeError):
          windows_bundle.create_deterministic_archive(
              bundle, Path(temporary_directory) / "bundle.zip"
          )

  def test_inno_staging_reuses_bundle_and_rejects_missing_bundle(self) -> None:
    """Stage valid bundles and reject missing or unsafe bundles."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      bundle = _make_valid_bundle(root)
      logo = root / "logo.ico"
      logo.write_bytes(b"logo")
      staging = root / "staging"
      windows_bundle.prepare_inno_staging(bundle, staging, logo)
      self.assertEqual(
          (staging / "inno-sources/launch_pymol.cmd").read_text(), "launch"
      )
      self.assertEqual((staging / "inno-assets/logo.ico").read_bytes(), b"logo")
      with self.assertRaises(FileNotFoundError):
        windows_bundle.prepare_inno_staging(root / "missing", staging, logo)
      (bundle / "library.zip").write_bytes(b"cx_Freeze")
      with self.assertRaises(RuntimeError):
        windows_bundle.prepare_inno_staging(bundle, staging, logo)

  def test_packaging_rejects_missing_runtime_and_incomplete_manifest(self) -> None:
    """Reject missing runtime files and incomplete manifests."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      bundle = _make_valid_bundle(root)
      archive = root / "bundle.zip"
      archive.write_bytes(b"stale archive")
      (bundle / "runtime/python/python.exe").unlink()
      with self.assertRaises(RuntimeError):
        windows_bundle.create_deterministic_archive(bundle, archive)
      self.assertFalse(archive.exists())

      bundle = _make_valid_bundle(root)
      staging = root / "staging"
      staging.mkdir()
      (staging / "stale.txt").write_text("stale")
      manifest = json.loads((bundle / "manifest.json").read_text())
      del manifest["dependency_sources"]
      (bundle / "manifest.json").write_text(json.dumps(manifest))
      with self.assertRaises(RuntimeError):
        windows_bundle.prepare_inno_staging(bundle, staging, root / "logo.ico")
      self.assertFalse(staging.exists())

  def test_packaging_rejects_each_missing_overlay(self) -> None:
    """Reject every bundle missing one required overlay."""
    overlay_targets = tuple(windows_bundle.overlay_inventory(Path("root")).values())
    for target in overlay_targets:
      with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        bundle = _make_valid_bundle(root)
        (bundle / target).unlink()
        archive = root / "bundle.zip"
        staging = root / "staging"
        staging.mkdir()
        logo = root / "logo.ico"
        logo.write_bytes(b"logo")

        with self.assertRaisesRegex(RuntimeError, "missing required content"):
          windows_bundle.create_deterministic_archive(bundle, archive)
        with self.assertRaisesRegex(RuntimeError, "missing required content"):
          windows_bundle.prepare_inno_staging(bundle, staging, logo)
        self.assertFalse(archive.exists())
        self.assertFalse(staging.exists())

  def test_packaging_rejects_stale_root_level_overlays(self) -> None:
    """Reject stale overlays placed at the bundle root."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      bundle = _make_valid_bundle(root)
      stale = bundle / "Lib/site-packages/pymol/base.css"
      stale.parent.mkdir(parents=True)
      stale.write_bytes(b"stale")
      archive = root / "bundle.zip"
      staging = root / "staging"
      staging.mkdir()
      logo = root / "logo.ico"
      logo.write_bytes(b"logo")

      with self.assertRaisesRegex(RuntimeError, "root-level overlay"):
        windows_bundle.create_deterministic_archive(bundle, archive)
      with self.assertRaisesRegex(RuntimeError, "root-level overlay"):
        windows_bundle.prepare_inno_staging(bundle, staging, logo)
      self.assertFalse(archive.exists())
      self.assertFalse(staging.exists())

  def test_packaging_rejects_provenance_and_lock_mutations(self) -> None:
    """Reject mutations to runtime, lock, and dependency provenance."""
    mutations = (
        ("runtime hash", lambda manifest: manifest["runtime"].update(
            sha256="0" * 64
        )),
        ("lock hash", lambda manifest: manifest.update(lock_sha256="0" * 64)),
        ("dependency version", lambda manifest: manifest["dependencies"].__setitem__(
            0, "numpy==9.9.9"
        )),
        ("dependency URL", lambda manifest: manifest["dependency_sources"]["numpy"][0].update(
            url="https://example.invalid/stale.whl"
        )),
        ("dependency hash", lambda manifest: manifest["dependency_sources"]["numpy"][0].update(
            sha256="sha256:" + "0" * 64
        )),
    )
    for name, mutate in mutations:
      with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        bundle = _make_valid_bundle(root)
        manifest = json.loads((bundle / "manifest.json").read_text())
        mutate(manifest)
        (bundle / "manifest.json").write_text(json.dumps(manifest))
        archive = root / "bundle.zip"
        staging = root / "staging"
        staging.mkdir()
        (root / "logo.ico").write_text("logo")
        with self.assertRaises(RuntimeError):
          windows_bundle.create_deterministic_archive(bundle, archive)
        with self.assertRaises(RuntimeError):
          windows_bundle.prepare_inno_staging(bundle, staging, root / "logo.ico")
        self.assertFalse(archive.exists())
        self.assertFalse(staging.exists())

  def test_packaging_rejects_stale_git_commit_and_timestamp(self) -> None:
    """Reject stale Git commit and timestamp metadata."""
    for field, value in (("git_commit", "0" * 40), ("timestamp", "stale")):
      with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        bundle = _make_valid_bundle(root)
        manifest = json.loads((bundle / "manifest.json").read_text())
        manifest[field] = value
        (bundle / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(RuntimeError):
          windows_bundle.create_deterministic_archive(bundle, root / "bundle.zip")

  def test_x64_inno_script_contract(self) -> None:
    """Verify the x64 Inno Setup script contract."""
    script = (
        pymakefile._PROJECT_ROOT / "os_specific/windows/inno_setup/setup_x64.iss"
    ).read_text(encoding="utf-8")
    self.assertIn("inno-sources", script)
    self.assertIn("launch_pymol.cmd", script)
    self.assertNotIn("VC_redist", script)
    self.assertNotIn("[Run]", script)

  def test_workflow_artifact_uploads_fail_on_missing_files(self) -> None:
    """Require workflow artifact uploads to fail on missing files."""
    workflow = (
        pymakefile._PROJECT_ROOT / ".github/workflows/build_app.yaml"
    ).read_text(encoding="utf-8")
    self.assertEqual(
        workflow.count("uses: actions/upload-artifact@v4"),
        workflow.count("if-no-files-found: error"),
    )
    self.assertIn("win_arch: ['x64']", workflow)
    self.assertNotIn("win_arch: ['x86', 'x64']", workflow)
    self.assertIn("python pymakefile.py build_windows_artifacts", workflow)
    self.assertIn("name: Verify pymake interpreter", workflow)
    self.assertNotIn(".\\pymake.bat build_windows_bundle", workflow)
    self.assertNotIn(".\\pymake.bat package_windows_bundle", workflow)
    self.assertNotIn(".\\pymake.bat prepare_inno_setup", workflow)
    self.assertLess(
        workflow.index("Setup Python 3.11"),
        workflow.index("Verify pymake interpreter"),
    )
    self.assertLess(
        workflow.index("Verify pymake interpreter"),
        workflow.index("python pymakefile.py build_windows_artifacts"),
    )
    project = tomllib.loads(
        (pymakefile._PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    inno_setup = (
        pymakefile._PROJECT_ROOT / "os_specific/windows/inno_setup/setup_x64.iss"
    ).read_text(encoding="utf-8")
    output_template = next(
        line.split("=", 1)[1]
        for line in inno_setup.splitlines()
        if line.startswith("OutputBaseFilename=")
    )
    expected_installer = output_template.replace(
        "{#MyAppVersion}", project["project"]["version"]
    ) + ".exe"
    workflow_installer_template = output_template.replace(
        "{#MyAppVersion}", "${{ env.PROJECT_VERSION }}"
    ) + ".exe"
    self.assertIn(
        "name: PyMOL-Open-Source-Windows-x86_64-Installer\n"
        "          if-no-files-found: error\n"
        f"          path: ./os_specific/dist/{workflow_installer_template}",
        workflow,
    )
    changed_version = "9.9.9+4"
    self.assertEqual(
        workflow_installer_template.replace(
            "${{ env.PROJECT_VERSION }}", changed_version
        ),
        output_template.replace("{#MyAppVersion}", changed_version) + ".exe",
    )
    self.assertIn(
        "name: PyMOL-Open-Source-Windows-x86_64-Portable-ZIP\n"
        "          if-no-files-found: error\n"
        "          path: ./dist/PyMOL-Open-Source_windows-x86_64.zip",
        workflow,
    )
    self.assertEqual(
        workflow_installer_template.replace(
            "${{ env.PROJECT_VERSION }}", project["project"]["version"]
        ),
        expected_installer,
    )
    self.assertNotIn("./os_specific/dist/*", workflow)
    self.assertNotIn("Windows-x86_64-Setup", workflow)
    self.assertIn(
        '-OutFile "$env:RUNNER_TEMP\\innosetup-6.7.3.exe"', workflow
    )
    self.assertIn(
        '& "$env:RUNNER_TEMP\\innosetup-6.7.3.exe" /SILENT', workflow
    )
    expected_inno_hash = "9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732"
    self.assertIn(expected_inno_hash, workflow)
    self.assertIn("Get-FileHash -Algorithm SHA256", workflow)
    self.assertIn("if ($actualHash -ne $expectedHash)", workflow)
    self.assertLess(
        workflow.index("Download Inno Setup installer"),
        workflow.index("Verify Inno Setup installer checksum"),
    )
    self.assertLess(
        workflow.index("Verify Inno Setup installer checksum"),
        workflow.index("Install Inno Setup"),
    )
    self.assertNotIn("-OutFile inno-setup.exe", workflow)
    self.assertNotIn(".\\inno-setup.exe /SILENT", workflow)
    self.assertIn(
        'C:\\Program Files (x86)\\Inno Setup 6', workflow
    )
    self.assertNotIn("\n          iscc ", workflow)
    self.assertNotIn("python pymakefile.py build_windows_bundle", workflow)
    self.assertNotIn("python pymakefile.py package_windows_bundle", workflow)
    self.assertNotIn("python pymakefile.py prepare_inno_setup", workflow)
    self.assertNotIn("Compile .iss file", workflow)

  def test_windows_docs_and_uv_workflow_pin_match_supported_flow(self) -> None:
    """Keep Windows documentation and workflow pins aligned."""
    workflow = (
        pymakefile._PROJECT_ROOT / ".github/workflows/build_app.yaml"
    ).read_text(encoding="utf-8")
    lock = tomllib.loads(
        (pymakefile._PROJECT_ROOT / "uv.lock").read_text(encoding="utf-8")
    )
    locked_uv_version = next(
        package["version"]
        for package in lock["package"]
        if package["name"] == "uv"
    )
    workflow_uv_version = next(
        line.split('"', 2)[1]
        for line in workflow.splitlines()
        if line.strip().startswith("version:")
    )
    self.assertEqual(workflow_uv_version, locked_uv_version)

    readme = (pymakefile._PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    windows_prerequisites = readme.split(
        "### Prerequisites for Windows\n", 1
    )[1].split("### Prerequisites for Linux\n", 1)[0]
    self.assertIn("clean checkout", windows_prerequisites)
    self.assertIn("native Windows x64 build environment", windows_prerequisites)
    self.assertIn("uv 0.12.3", windows_prerequisites)
    self.assertNotIn("requirements.txt", windows_prerequisites)
    self.assertNotIn("cx_Freeze", windows_prerequisites)
    windows_section = readme.split("#### Windows\n", 1)[1].split(
        "#### macOS\n", 1
    )[0]
    for command in (
        "python pymakefile.py build_windows_bundle",
        "python pymakefile.py package_windows_bundle",
        "python pymakefile.py prepare_inno_setup",
        "setup_x64.iss",
    ):
      self.assertIn(command, windows_section)
    self.assertIn("Windows x86 CI and packaging are retired and unsupported", windows_section)
    self.assertIn("cx_Freeze `build_app`", windows_section)
    self.assertNotIn("pymake.bat build_app", windows_section)
    self.assertNotIn("requirements.txt", windows_section)
    self.assertIn("Installer execution, installation, and shortcut validation", windows_section)
    self.assertNotIn("architecture=x86", windows_section)

    poc = (
        pymakefile._PROJECT_ROOT
        / "docs/features/uv-standalone-bundle/windows-x86_64-poc.md"
    ).read_text(encoding="utf-8")
    self.assertIn("uv 0.12.3", poc)
    for command in (
        "python pymakefile.py build_windows_bundle",
        "python pymakefile.py package_windows_bundle",
        "python pymakefile.py prepare_inno_setup",
    ):
      self.assertIn(command, poc)
    self.assertIn("runtime/python/Lib/site-packages/...", poc)
    self.assertIn("Windows x86 CI/package coverage is retired", poc)
    self.assertIn(
        "Installer execution, installation, and shortcut validation remain human-owned",
        poc,
    )
    self.assertNotIn(".\\pymake.bat build_windows_bundle", poc)

  def test_platform_build_paths(self) -> None:
    """Resolve platform-specific build paths and commands."""
    with mock.patch.object(pymakefile.platform, "system", return_value="Darwin"):
      with mock.patch.object(
          pymakefile.sysconfig,
          "get_path",
          return_value="/tmp/venv/lib/python3.11/site-packages",
      ):
        platform_dir, package_dir, build_command = (
          pymakefile._platform_build_paths()
        )

    self.assertEqual(platform_dir, pymakefile._PROJECT_ROOT / "os_specific/macos")
    self.assertEqual(
      package_dir,
      Path("/tmp/venv/lib/python3.11/site-packages/pymol"),
    )
    self.assertEqual(build_command, "bdist_mac")

  def test_build_app_copies_customizations_and_artifacts(self) -> None:
    """Copy customizations and built artifacts into the application tree."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      package_dir = root / "venv/lib/python3.11/site-packages/pymol"
      (package_dir / "data/pymol/icons").mkdir(parents=True)
      (package_dir.parent / "pmg_qt").mkdir()
      (root / "edited/pmg_qt").mkdir(parents=True)
      (root / "edited/pymol/data/pymol").mkdir(parents=True)
      (root / "alternative_design").mkdir()
      (root / "os_specific/linux").mkdir(parents=True)
      (root / "os_specific/linux/build").mkdir()
      (root / "os_specific/linux/build/artifact").write_text("built")

      source_paths = (
        root / "edited/pmg_qt/pymol_qt_gui.py",
        root / "edited/pymol/data/pymol/base.css",
        root / "edited/pymol/__init__.py",
        root / "edited/pymol/startup_wrapper.py",
        root / "alternative_design/alt_logo.png",
        root / "os_specific/linux/splash.png",
      )
      for source_path in source_paths:
        source_path.write_text(source_path.name)

      with mock.patch.object(pymakefile, "_PROJECT_ROOT", root):
        with mock.patch.object(
            pymakefile.platform, "system", return_value="Linux"
        ):
          with mock.patch.object(
              pymakefile.sysconfig,
              "get_path",
              return_value=str(package_dir.parent),
          ):
            with mock.patch.object(pymakefile, "_run_process") as run_process:
              pymakefile.build_app()

      self.assertTrue((package_dir / "base.css").exists())
      self.assertTrue((package_dir / "startup_wrapper.py").exists())
      self.assertTrue((package_dir / "data/pymol/splash.png").exists())
      self.assertTrue((root / "dist/artifact").exists())
      run_process.assert_called_once()
      self.assertEqual(run_process.call_args.kwargs["cwd"], root / "os_specific/linux")

  def test_prepare_inno_setup_uses_bundle_staging_tree(self) -> None:
    """Prepare Inno Setup staging from an existing bundle."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      bundle = root / "dist/windows-x86_64-bundle"
      bundle.mkdir(parents=True)
      valid_bundle = _make_valid_bundle(root / "source")
      shutil.copytree(valid_bundle, bundle, dirs_exist_ok=True)
      manifest_timestamp = json.loads(
          (bundle / "manifest.json").read_text(encoding="utf-8")
      )["timestamp"]
      bundle_commit = json.loads(
          (bundle / "manifest.json").read_text(encoding="utf-8")
      )["git_commit"]
      shutil.copy2(pymakefile._PROJECT_ROOT / "uv.lock", root / "uv.lock")
      (root / "os_specific/windows").mkdir(parents=True)
      (root / "os_specific/windows/logo.ico").write_text("logo")

      with mock.patch.object(pymakefile, "_PROJECT_ROOT", root), mock.patch.object(
          pymakefile.platform, "system", return_value="Windows"
      ), mock.patch.object(
          windows_bundle,
          "_commit_timestamp",
          return_value=manifest_timestamp,
      ), mock.patch.object(
          windows_bundle.subprocess,
          "check_output",
          return_value=bundle_commit + "\n",
      ):
        pymakefile.prepare_inno_setup()

      staging = root / "inno-build-release"
      self.assertTrue((staging / "inno-sources/launch_pymol.cmd").exists())
      self.assertTrue((staging / "inno-assets/logo.ico").exists())

  def test_package_task_uses_existing_bundle_without_rebuild(self) -> None:
    """Package an existing bundle without rebuilding it."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      bundle = root / "dist/windows-x86_64-bundle"
      bundle.mkdir(parents=True)
      (bundle / "manifest.json").write_text(
          '{"target": "windows-x86_64"}\n', encoding="utf-8"
      )
      (bundle / "launch_pymol.cmd").write_text("launch", encoding="utf-8")
      with mock.patch.object(pymakefile, "_PROJECT_ROOT", root), mock.patch.object(
          pymakefile.platform, "system", return_value="Windows"
      ), mock.patch("scripts.python.windows_bundle.create_deterministic_archive") as archive:
        pymakefile.package_windows_bundle()
      archive.assert_called_once_with(
          bundle,
          root / "dist" / windows_bundle.ARCHIVE_NAME,
          mock.ANY,
      )

  def test_prepare_inno_setup_requires_bundle(self) -> None:
    """Require a bundle before preparing Inno Setup staging."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      (root / "os_specific/windows").mkdir(parents=True)
      (root / "os_specific/windows/logo.ico").write_text("logo")
      with mock.patch.object(pymakefile, "_PROJECT_ROOT", root), mock.patch.object(
          pymakefile.platform, "system", return_value="Windows"
      ):
        with self.assertRaises(FileNotFoundError):
          pymakefile.prepare_inno_setup()

  def test_old_x86_inno_preparation_remains_available(self) -> None:
    """Preserve the legacy x86 staging helper behavior."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      app_build = root / f"dist/exe.win-amd64-{sys.version_info.major}.{sys.version_info.minor}"
      app_build.mkdir(parents=True)
      (app_build / "Open-Source-PyMOL.exe").write_text("built")
      (root / "os_specific/windows").mkdir(parents=True)
      (root / "os_specific/windows/logo.ico").write_text("logo")
      (root / "vendor/microsoft").mkdir(parents=True)
      (root / "vendor/microsoft/VC_redist.x64.exe").write_text("redist")
      with mock.patch.object(pymakefile, "_PROJECT_ROOT", root):
        pymakefile._prepare_inno_setup_environment()

      staging = root / "inno-build-release"
      self.assertTrue(
        (staging / "inno-sources/Open-Source-PyMOL.exe").exists()
      )
      self.assertTrue(
        (staging / "inno-sources/VC_redist.x64.exe").exists()
      )
      self.assertTrue((staging / "inno-assets/logo.ico").exists())

  def test_build_inno_setup_rejects_unknown_architecture(self) -> None:
    """Reject unsupported installer architectures."""
    with mock.patch.object(pymakefile.platform, "system", return_value="Windows"):
      with self.assertRaises(ValueError):
        pymakefile.build_inno_setup("arm64")

  def test_build_inno_setup_rejects_retired_x86_before_build_work(self) -> None:
    """Reject retired x86 builds before invoking build steps."""
    with mock.patch.object(
        pymakefile.platform, "system", return_value="Windows"
    ), mock.patch.object(
        pymakefile, "_prepare_inno_setup_environment"
    ) as prepare, mock.patch.object(
        pymakefile, "_run_process"
    ) as run_process, mock.patch.object(
        pymakefile.shutil, "which"
    ) as which:
      with self.assertRaisesRegex(RuntimeError, "x86.*retired"):
        pymakefile.build_inno_setup("x86")

    prepare.assert_not_called()
    run_process.assert_not_called()
    which.assert_not_called()

  def test_run_accepts_explicit_working_directory(self) -> None:
    """Pass an explicit working directory to subprocess execution."""
    with mock.patch.object(pymakefile.subprocess, "run") as run_process:
      pymakefile.run("pytest", cwd=pymakefile._PROJECT_ROOT)

    self.assertEqual(
      run_process.call_args.kwargs["cwd"],
      pymakefile._PROJECT_ROOT,
    )


if __name__ == "__main__":
  unittest.main()
