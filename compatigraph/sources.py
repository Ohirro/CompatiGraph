import re
from collections.abc import Iterator
from functools import singledispatch
from pathlib import Path
from typing import Any

import requests


def is_url_accessible(url: str) -> bool:
    try:
        response = requests.head(url, timeout=10)
        if response.status_code == 404:
            return False
        return True
    except requests.RequestException:
        return False


@singledispatch
def _find_all_sources(path: Any) -> Iterator[Path]:
    raise NotImplementedError("Unsupported type")


@_find_all_sources.register
def _(path: str) -> Iterator[Path]:
    sources_files = list(Path(path).rglob("*.sources"))
    return iter(sources_files) if sources_files else iter(Path(path).rglob("*.list"))


@_find_all_sources.register
def _(path: Path) -> Iterator[Path]:
    sources_files = list(path.rglob("*.sources"))
    return iter(sources_files) if sources_files else iter(path.rglob("*.list"))


class SourceHandler:
    def __init__(self, sources_location: str | Path = None) -> None:
        self.sources_location: Path | str = sources_location
        if sources_location is None:
            self.sources_location = Path("/etc/apt")

    @staticmethod
    def parse_sources_list(file_path: Path) -> dict[str, tuple[str, list, str]]:
        repositories: dict[str, tuple[str, list, str]] = {}
        if file_path.suffix == ".list":
            with open(file_path, "r", encoding="utf8") as file:
                for line in file:
                    if line.strip() and not line.strip().startswith("#"):
                        match = re.match(r"deb\s*(?:\[\s*(.*?)\s*\])?\s*(\S+)\s+(\S+)\s+(.+)", line.strip())
                        if match:
                            repository_url = match.group(2)
                            release = match.group(3)
                            components = match.group(4).split()
                            if "updates" in release:
                                continue
                            repositories[repository_url] = (release, components)
        elif file_path.suffix == ".sources":
            with open(file_path, "r", encoding="utf8") as file:
                repository_url = None
                release = None
                for line in file:
                    if not (line := line.strip()):
                        continue
                    if line.startswith("URIs:"):
                        repository_url = line.split(": ")[1]
                    elif line.startswith("Suites:"):
                        release = line.split(": ")[1]
                    elif line.startswith("Components:"):
                        components = line.split(": ")[1].split()
                        for rel in release.split():
                            repositories[repository_url] = (rel, components)
                        release = None
                        repository_url = None
        return repositories

    def make_packages_url(self, base_url: str, release: str, component: str, architecture: str = "amd64") -> str:
        if is_url_accessible(
            f"{base_url}/dists/{release.replace(' ', '-')}/{component}/binary-{architecture}/Packages.xz"
        ):
            return f"{base_url}/dists/{release.replace(' ', '-')}/{component}/binary-{architecture}/Packages.xz"
        return f"{base_url}/dists/{release.replace(' ', '-')}/{component}/binary-{architecture}/Packages.gz"

    def system_links(self) -> list[str]:
        res: dict[str, tuple[str, str]] = {}
        for sources in _find_all_sources(self.sources_location):
            res.update(self.parse_sources_list(sources))
        links: list[str] = []
        for base_url, meta in res.items():
            for component in meta[1]:
                links.append(self.make_packages_url(base_url, meta[0], component))
        return links


if __name__ == "__main__":
    sh = SourceHandler()
    print(sh.system_links())