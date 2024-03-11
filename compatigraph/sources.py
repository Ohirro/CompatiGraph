import re
from pathlib import Path
from collections.abc import Iterator
from typing import Any
from functools import singledispatch
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
                        repositories[repository_url] = (release.split(), components)
                        release = None
                        repository_url = None
        print(repositories)
        return repositories

    def make_packages_url(self, base_url: str, releases: list[str], components: list[str], architecture: str = "amd64") -> str:
        links = []
        for release in releases:
            # for component in components:
                component = "main"
                if is_url_accessible(f"{base_url}/dists/{release.replace(' ', '-')}/{component}/binary-{architecture}/Packages.xz"):
                    links.append(f"{base_url}/dists/{release.replace(' ', '-')}/{component}/binary-{architecture}/Packages.xz")
                links.append(f"{base_url}/dists/{release.replace(' ', '-')}/{component}/binary-{architecture}/Packages.gz")
        print(links)
        return links

    def system_links(self) -> list[str]:
        res: dict[str, tuple[str, str]] = {}
        for sources in _find_all_sources(self.sources_location):
            res.update(self.parse_sources_list(sources))
        links: list[str] = []
        for base_url, meta in res.items():
            links = self.make_packages_url(base_url, meta[0], meta[1])
        return links
