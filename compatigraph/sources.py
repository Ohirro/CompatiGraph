import re
from pathlib import Path
from typing import Union, Iterator, Any
from functools import singledispatch


@singledispatch
def _find_all_sources(path: Any):
    raise NotImplementedError("Unsupported type")


@_find_all_sources.register
def _(path: str) -> Iterator[Path]:
    return Path(path).rglob("*.list")


@_find_all_sources.register
def _(path: Path) -> Iterator[Path]:
    return path.rglob("*.list")


class SourceHandler:
    def __init__(self, sources_location: Union[str, Path]) -> None:
        self.sources_location = sources_location

    @staticmethod
    def parse_sources_list(file_path: Path):
        repositories = {}
        with open(file_path, "r") as file:
            for line in file:
                if line.strip() and not line.strip().startswith("#"):
                    match = re.match(r"deb\s+(\S+)\s+(\S+)\s+(\w+)\s*", line.strip())
                    if match:
                        repository_url = match.group(1)
                        release = match.group(2)
                        component = match.group(3)
                        if "updates" in release:
                            continue
                        repositories[release] = (repository_url, component)
        return repositories

    def make_packages_url(self, base_url: str, release: str, architecture: str = "amd64"):
        packages_url = f"{base_url}/dists/{release}/main/binary-{architecture}/Packages.gz"
        return packages_url

    def get_the_links(self):
        res = {}
        for sources in _find_all_sources(self.sources_location):
            res.update(self.parse_sources_list(sources))
        links = []
        for rel, meta in res.items():
            links.append(self.make_packages_url(meta[0], rel))
        return links
