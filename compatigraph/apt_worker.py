import subprocess
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

        :param other_version: Строка с версией для проверки.
        :return: True, если условие удовлетворено, иначе False.
        """
        other_version = debian_support.Version(other_version)

        if self.operator == '=':
            return self.version == other_version
        elif self.operator == '>>':
            return other_version > self.version
        elif self.operator == '>=':
            return other_version >= self.version
        elif self.operator == '<<':
            return other_version < self.version
        elif self.operator == '<=':
            return other_version <= self.version
        elif self.operator == 'any':
            return True
        else:
            raise ValueError(f"Неизвестный оператор: {self.operator}")

class AptExecutor:

    def __init__(self, reqursive: bool = True) -> None:
        self.reqursive = reqursive

    def get_dependencies(self, package_name):
        """
        Get all dependencies for a given package on Debian-based systems.
        """
        try:
            if self.reqursive:
                result = subprocess.run(['apt-rdepends', package_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            # else:
                # TODO to think about
                # result = subprocess.run(['apt-depends', package_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return result.stdout.decode('utf-8')
        except subprocess.CalledProcessError as e:
            raise subprocess.CalledProcessError from e


class DepHandler:

    def __init__(self) -> None:
        ...

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
                    dependencies[dep_name] = {'=': [], '>=': [], '<=': [], 'any': [], '<<':[], '>>':[]}
                dependency = Dependency(operator, version, current_package)
                dependencies[dep_name][operator].append(dependency)

        # Сортировка не применяется к 'any', так как версия не указана
        for dep_name, operators in dependencies.items():
            for operator, deps in operators.items():
                if operator != 'any':
                    deps.sort(key=lambda d: debian_support.Version(d.version) if d.version else debian_support.Version("0"))

        return dependencies

    def get_dependencies(self, package_name):
        """
        Get all dependencies for a given package on Debian-based systems.
        """
        try:
            result = subprocess.run(['apt-rdepends', package_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            dependencies = result.stdout.decode('utf-8')

            return self.parse_dependencies_detailed(dependencies)
        except subprocess.CalledProcessError as e:
            print(f"Error occurred: {e}")
        return {}


