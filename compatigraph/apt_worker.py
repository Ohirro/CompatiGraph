import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from subprocess import Popen
from typing import Generator, Tuple
import tqdm


from debian import debian_support


class Dependency:
    def __init__(self, operator, version, package):
        self.operator = operator
        self.version = debian_support.Version(version) if version else None
        self.package = package

    def __repr__(self):
        return f"Dependency(operator='{self.operator}', version='{self.version}', package='{self.package}')"

    def is_satisfied_by(self, other_version):
        """
        Проверяет, удовлетворяет ли переданная версия условию зависимости.

        :other_version: Строка с версией для проверки.
        :return: True, если условие удовлетворено, иначе False.
        """
        other_version = debian_support.Version(other_version)

        if self.operator == "=":
            return self.version == other_version
        if self.operator == ">>":
            return other_version > self.version
        if self.operator == ">=":
            return other_version >= self.version
        if self.operator == "<<":
            return other_version < self.version
        if self.operator == "<=":
            return other_version <= self.version
        if self.operator == "any":
            return other_version is not None
        raise ValueError(f"Неизвестный оператор: {self.operator}")


class DepHandler:
    def __init__(self) -> None: ...

    @staticmethod
    def parse_dependencies_detailed(deps):
        dependencies = {}
        current_package = None
        for line in deps.split("\n"):
            line = line.strip()
            if line and not line.startswith("Depends:"):
                current_package = line
            elif line.startswith("Depends:"):
                dep_info = line.replace("Depends: ", "").split(" (", 1)
                dep_name = dep_info[0].strip()
                if len(dep_info) > 1:
                    version_info = dep_info[1].rstrip(")").split(" ", 1)
                    if len(version_info) == 2:
                        operator, version = version_info
                    else:
                        operator, version = "=", version_info[0] if version_info else "any"
                else:
                    operator, version = "any", "0"  # Для зависимостей без указанной версии

                if dep_name not in dependencies:
                    dependencies[dep_name] = {"=": [], ">=": [], "<=": [], "any": [], "<<": [], ">>": []}
                dependency = Dependency(operator, version, current_package)
                dependencies[dep_name][operator].append(dependency)

        # Сортировка не применяется к 'any', так как версия не указана
        for dep_name, operators in dependencies.items():
            for operator, deps_ in operators.items():
                if operator != "any":
                    deps_.sort(
                        key=lambda d: debian_support.Version(d.version) if d.version else debian_support.Version("0")
                    )

        return dependencies

    def load_from_local_repo(self) -> Generator[Tuple[str, str]]:
        # TODO to think about process_optimization
        with TemporaryDirectory() as tmp_dir:
            for file in Path("/var/lib/apt/lists").rglob(".lz4"):
                err_out = ""
                with Popen(
                    f"sudo lz4 -d {file} {tmp_dir}/{file}_extracted".split(),
                    stdout=subprocess.DEVNULL,
                    stderr=err_out,
                ) as proc:
                    if not proc.returncode:
                        # TODO find correct exception
                        raise ValueError(f"Unable to unpack file\n context is \n\n {err_out}\n\n")
                    with open(f"{tmp_dir}/{file}_extracted", "r", encoding="utf-8") as file_io:
                        yield (file, file_io.read())
