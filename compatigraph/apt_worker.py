import subprocess
from pathlib import Path
from subprocess import Popen
from tempfile import TemporaryDirectory
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
    def __init__(self) -> None:
        ...

    def parse_dependencies_detailed(self, deps_line, package_name):
        print(deps_line, package_name)
        dependencies = {}
        dep_name, dependency = self._parse_dependency_line(deps_line, package_name)
        if dep_name not in dependencies:
            dependencies[dep_name] = self._init_dependency_struct()
        dependencies[dep_name][dependency.operator].append(dependency)
        self._sort_dependencies(dependencies)
        return dependencies

    def _parse_dependency_line(self, line, current_package):
        dep_info = line.replace("Depends: ", "").split(" (", 1)
        dep_name = dep_info[0].strip()
        if len(dep_info) > 1:
            version_info = dep_info[1].rstrip(")").split(" ", 1)
            operator, version = version_info if len(version_info) == 2 else ("=", version_info[0])
        else:
            operator, version = "any", "0"
        return dep_name, Dependency(operator, version, current_package)

    def _init_dependency_struct(self):
        return {"=": [], ">=": [], "<=": [], "any": [], "<<": [], ">>": []}

    def _sort_dependencies(self, dependencies):
        for operators in dependencies.values():
            for operator, deps in operators.items():
                if operator != "any":
                    deps.sort(key=lambda d: debian_support.Version(
                        d.version) if d.version != "any" else debian_support.Version("0"))


class RepositoryFileHandler:
    @staticmethod
    def extract_and_read_files(source_path="/var/lib/apt/lists"):
        with TemporaryDirectory() as tmp_dir:
            for file in Path(source_path).rglob("*.lz4"):
                extracted_file = Path(tmp_dir) / (file.stem + "_extracted")
                subprocess.run(["lz4", "-d", str(file), str(extracted_file)],
                               stdout=subprocess.DEVNULL, check=True)
                with open(extracted_file, "r", encoding="utf-8") as file_io:
                    yield file.name, file_io.readlines()
    @staticmethod
    def use_if_not_lz4(source_path="/var/lib/apt/lists"):
        for file in Path(source_path).rglob("*Packages"):
            with open(file, "r", encoding="utf-8") as file_io:
                yield file.name, file_io.readlines()
