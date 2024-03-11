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
    def parse_sources_list(file_path: Path) -> Dict[str, Tuple[str, list, str]]:
        repositories: Dict[str, Tuple[str, list, str]] = {}
        if file_path.suffix == ".list":
            with open(file_path, "r") as file:
                for line in file:
                    if line.strip() and not line.strip().startswith("#"):
                        match = re.match(
                            r"deb\s*(?:\[\s*(.*?)\s*\])?\s*(\S+)\s+(\S+)\s+(.+)",
                            line.strip())
                        if match:
                            attributes = match.group(1)  # This captures everything within the brackets
                            repository_url = match.group(2)
                            release = match.group(3)
                            components = match.group(4).split()  # Splits the components into a list
                            
                            if "updates" in release:
                                continue
                            
                            # Simply store the components list as it is
                            repositories[release] = (repository_url, components, attributes)
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
                        components = line.split(': ')[1].split()  # Split components into a list
                        for rel in release.split():
                            repositories[rel] = (repository_url, components)
                        release = None
                        repository_url = None
                        component = None
        return repositories

    def make_packages_url(self, base_url: str, release: str, component: str, architecture: str = "amd64") -> str:
        if is_url_accessible(f"{base_url}/dists/{release.replace(' ', '-')}/main/binary-{architecture}/Packages.xz"):
            return f"{base_url}/dists/{release.replace(' ', '-')}/main/binary-{architecture}/Packages.xz"
        return f"{base_url}/dists/{release.replace(' ', '-')}/main/binary-{architecture}/Packages.gz"

        
    def system_links(self) -> List[str]:
        res: Dict[str, Tuple[str, str]] = {}
        for sources in _find_all_sources(self.sources_location):
            res.update(self.parse_sources_list(sources))
        links: List[str] = []
        for rel, meta in res.items():
            for component in meta[1]:
                links.append(self.make_packages_url(meta[0], rel, component))
        return links
