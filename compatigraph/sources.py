import re
from pathlib import Path
from typing import Union, Iterator, Any, Dict, Tuple, List
from functools import singledispatch
import requests


def is_url_accessible(url: str) -> bool:
    try:
        response = requests.head(url)
        if response.status_code == 404:
            return False
        else:
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
    def __init__(self, sources_location: Union[str, Path] = None) -> None:
        self.sources_location: Union[Path, str] = sources_location
        if sources_location is None:
            self.sources_location = Path("/etc/apt")

    @staticmethod
    def parse_sources_list(file_path: Path) -> Dict[str, Tuple[str, str]]:
        repositories: Dict[str, Tuple[str, str]] = {}
        if file_path.suffix == ".list":
            # Existing logic for .list files
            pass
        elif file_path.suffix == ".sources":
            with open(file_path, "r") as file:
                repository_url = None
                release = None
                component = None
                for line in file:
                    line = line.strip()
                    if not line:
                        continue
                    elif line.startswith('URIs:'):
                        repository_url = line.split(': ')[1]
                    elif line.startswith('Suites:'):
                        release = line.split(': ')[1]
                    elif line.startswith('Components:'):
                        component = line.split(': ')[1]
                        if release and repository_url and component:
                            for rel in release.split():
                                repositories[rel] = (repository_url, component)
                            release = None
                            repository_url = None
                            component = None
        return repositories

    def make_packages_url(self, base_url: str, release: str, architecture: str = "amd64") -> str:
        if is_url_accessible(f"{base_url}/dists/{release.replace(' ', '-')}/main/binary-{architecture}/Packages.xz"):
            return f"{base_url}/dists/{release.replace(' ', '-')}/main/binary-{architecture}/Packages.xz"
        return f"{base_url}/dists/{release.replace(' ', '-')}/main/binary-{architecture}/Packages.gz"

        
    def system_links(self) -> List[str]:
        res: Dict[str, Tuple[str, str]] = {}
        for sources in _find_all_sources(self.sources_location):
            res.update(self.parse_sources_list(sources))
        links: List[str] = []
        for rel, meta in res.items():
            links.append(self.make_packages_url(meta[0], rel))
        return links
