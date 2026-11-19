"""Template variables of the documentation website (mkdocs-macros plugin).

Name, version and repository come from pyproject.toml, so the website always
shows the version, file names and download links of the release it is built
for. Usage in the Markdown pages: {{ version }}, {{ app_dir }},
{{ file_name("_amd64.deb") }}, {{ download_link("_amd64.deb") }}
"""
import pathlib
import tomllib

PYPROJECT_FILEPATH = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"
# Suffixes of the release files (see the build scripts); a typo fails the build
RELEASE_FILE_SUFFIXES = (
  "_x64_setup.exe", "_x64_portable.zip",
  "_macOS_AppleSilicon.dmg", "_macOS_Intel.dmg",
  "_amd64.deb", "_x86_64.rpm", ".tar.gz",
)


def define_env(env) -> None:
  """Defines the variables and macros that the Markdown pages can use."""
  with open(PYPROJECT_FILEPATH, "rb") as tmp_file:
    project = tomllib.load(tmp_file)["project"]
  name = project["name"]
  version = project["version"]
  repository_url = project["urls"]["Repository"]
  env.variables["version"] = version
  env.variables["repository_url"] = repository_url
  # Directory of the installation (/opt/...) and of the extracted .tar.gz
  env.variables["app_dir"] = f"{name}-{version}"

  @env.macro
  def file_name(suffix: str) -> str:
    """Returns the file name of a release file, e.g. file_name("_amd64.deb")."""
    if suffix not in RELEASE_FILE_SUFFIXES:
      raise ValueError(f"Unknown release file suffix: {suffix}")
    return f"{name}_v{version}{suffix}"

  @env.macro
  def download_link(suffix: str) -> str:
    """Returns a Markdown link that downloads a release file."""
    return f"[{file_name(suffix)}]({repository_url}/releases/download/v{version}/{file_name(suffix)})"
