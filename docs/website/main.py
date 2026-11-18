"""Template variables of the documentation website (mkdocs-macros plugin).

The version is read from pyproject.toml, so the website always shows the
version, file names and download links of the release it is built for.
Usage in the Markdown pages: {{ version }}, {{ file_name("_amd64.deb") }},
{{ download_url("_amd64.deb") }}
"""
import pathlib
import tomllib

REPOSITORY_URL = "https://github.com/kullik01/pymol-open-source-setup"
PYPROJECT_FILEPATH = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"


def define_env(env) -> None:
  """Defines the variables and macros that the Markdown pages can use."""
  with open(PYPROJECT_FILEPATH, "rb") as tmp_file:
    version = tomllib.load(tmp_file)["project"]["version"]
  env.variables["version"] = version
  env.variables["repository_url"] = REPOSITORY_URL

  @env.macro
  def file_name(suffix: str) -> str:
    """Returns the file name of a release file, e.g. file_name("_amd64.deb")."""
    return f"PyMOL-Open-Source_v{version}{suffix}"

  @env.macro
  def download_url(suffix: str) -> str:
    """Returns the direct download link of a release file."""
    return f"{REPOSITORY_URL}/releases/download/v{version}/{file_name(suffix)}"
