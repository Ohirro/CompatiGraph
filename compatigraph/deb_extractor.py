import os
import subprocess
import tarfile

from typing import List


class DepsExtractor:
    def __init__(self, deb_path: str = None) -> None:
        self.deb_path = deb_path

    def extract_dependencies_from_deb(self) -> List[str]:
        subprocess.run(["ar", "x", self.deb_path], check=True)

        control_archive_path = self._find_control_archive()

        dependencies = self._extract_dependencies(control_archive_path)

        self._cleanup_files(control_archive_path)

        return dependencies

    def _find_control_archive(self) -> str:
        for possible_path in ["control.tar.gz", "control.tar.xz"]:
            if os.path.exists(possible_path):
                return possible_path
        raise FileNotFoundError("Control archive not found.")

    def _extract_dependencies(self, archive_path: str) -> List[str]:
        mode = "r:gz" if archive_path.endswith(".gz") else "r:xz"
        with tarfile.open(archive_path, mode) as tar:
            tar.extract("control")

        dependencies = []
        with open("control", encoding="utf-8") as control_file:
            for line in control_file:
                if line.startswith(("Depends:", "Recommends:")):
                    dependencies = line.split(":", 1)[1].strip().split(", ")
                    break
        return dependencies

    def _cleanup_files(self, control_archive_path: str) -> None:
        os.remove(control_archive_path)
        os.remove("control")
        for file in ["data.tar.xz", "debian-binary"]:
            if os.path.exists(file):
                os.remove(file)
