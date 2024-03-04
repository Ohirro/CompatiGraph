from debian.debian_support import Version

from compatigraph.apt_worker import Dependency


class LogicSolver:
    def __init__(self) -> None:
        ...

    def analyze_dependencies(self, dependencies):
        equals = dependencies.get("=", [])
        greater_or_equals = dependencies.get(">=", [])
        less_or_equals = dependencies.get("<=", [])
        strictly_greater = dependencies.get(">>", [])
        strictly_less = dependencies.get("<<", [])
        conflicts = []

        # 1. Проверка "=" зависимостей на идентичность версий
        if len(set(dep.version for dep in equals)) > 1:
            conflicts.append(("=", equals))

        # 2. Сравнение ">=" и "<="
        if greater_or_equals and less_or_equals:
            if Version(greater_or_equals[0].version) > Version(less_or_equals[-1].version):
                conflicts.append((">= <=", [greater_or_equals[0], less_or_equals[-1]]))

        # 3. Сравнение ">>" и "<<"
        if strictly_greater and strictly_less:
            if Version(strictly_greater[0].version) <= Version(strictly_less[-1].version):
                conflicts.append((">> <<", [strictly_greater[0], strictly_less[-1]]))

        # 4. Совместимость "=" с другими операторами
        for eq_dep in equals:
            # Сравнение "=" с ">=", "<<", ">>", и "<="
            self.check_compatibility_with_equals(
                eq_dep, greater_or_equals, less_or_equals, strictly_greater, strictly_less, conflicts
            )

        # 5. Сравнение ">=" и ">>"
        if greater_or_equals and strictly_greater:
            if Version(greater_or_equals[0].version) > Version(strictly_greater[0].version):
                conflicts.append((">= >>", [greater_or_equals[0], strictly_greater[0]]))

        # 6. Сравнение "<=" и "<<"
        if less_or_equals and strictly_less:
            if Version(less_or_equals[-1].version) < Version(strictly_less[-1].version):
                conflicts.append(("<= <<", [less_or_equals[-1], strictly_less[-1]]))

        # 7. Сравнение ">=" и "<<"
        if greater_or_equals and strictly_less:
            if Version(greater_or_equals[0].version) <= Version(strictly_less[-1].version):
                conflicts.append((">= <<", [greater_or_equals[0], strictly_less[-1]]))

        # 8. Сравнение "<=" и ">>"
        if less_or_equals and strictly_greater:
            if Version(less_or_equals[-1].version) <= Version(strictly_greater[0].version):
                conflicts.append(("<= >>", [less_or_equals[-1], strictly_greater[0]]))

        # Возвращаем все найденные конфликты
        if conflicts:
            return False, conflicts

        # Все проверки пройдены, зависимости корректны
        return True, None

    @staticmethod
    def check_compatibility_with_equals(
        eq_dep, greater_or_equals, less_or_equals, strictly_greater, strictly_less, conflicts
    ):
        eq_version = Version(eq_dep.version)
        # "=" с ">="
        if greater_or_equals and eq_version < Version(greater_or_equals[0].version):
            conflicts.append(("= >=", [eq_dep, greater_or_equals[0]]))
        # "=" с "<="
        if less_or_equals and eq_version > Version(less_or_equals[-1].version):
            conflicts.append(("= <=", [eq_dep, less_or_equals[-1]]))
        # "=" с ">>"
        if strictly_greater and eq_version <= Version(strictly_greater[0].version):
            conflicts.append(("= >>", [eq_dep, strictly_greater[0]]))
        # "=" с "<<"
        if strictly_less and eq_version >= Version(strictly_less[-1].version):
            conflicts.append(("= <<", [eq_dep, strictly_less[-1]]))

    @staticmethod
    def find_strictest_conditions(dependencies):
        equals = dependencies.get("=", [])
        greater_or_equals = dependencies.get(">=", [])
        less_or_equals = dependencies.get("<=", [])
        strictly_greater = dependencies.get(">>", [])
        strictly_less = dependencies.get("<<", [])

        strictest_conditions = {}

        # Условие для "="
        if equals:
            versions = set(dep.version for dep in equals)
            if len(versions) == 1:
                version = versions.pop()
                package = equals[0].package  # Предполагаем, что все объекты в equals относятся к одному пакету
                strictest_conditions["="] = [Dependency("=", version, package)]
                return strictest_conditions
            else:
                raise ValueError("Conflicting '=' conditions")

        # Выбор наиболее строгого условия для ">"
        if strictly_greater and greater_or_equals:
            if Version(strictly_greater[0].version) > Version(greater_or_equals[0].version):
                strictest_conditions[">>"] = [
                    Dependency(">>", strictly_greater[0].version, strictly_greater[0].package)
                ]
            else:
                strictest_conditions[">="] = [
                    Dependency(">=", greater_or_equals[0].version, greater_or_equals[0].package)
                ]
        elif strictly_greater:
            strictest_conditions[">>"] = [Dependency(">>", strictly_greater[0].version, strictly_greater[0].package)]
        elif greater_or_equals:
            strictest_conditions[">="] = [Dependency(">=", greater_or_equals[0].version, greater_or_equals[0].package)]

        # Выбор наиболее строгого условия для "<"
        if strictly_less and less_or_equals:
            if Version(strictly_less[-1].version) < Version(less_or_equals[-1].version):
                strictest_conditions["<<"] = [Dependency("<<", strictly_less[-1].version, strictly_less[-1].package)]
            else:
                strictest_conditions["<="] = [Dependency("<=", less_or_equals[-1].version, less_or_equals[-1].package)]
        elif strictly_less:
            strictest_conditions["<<"] = [Dependency("<<", strictly_less[-1].version, strictly_less[-1].package)]
        elif less_or_equals:
            strictest_conditions["<="] = [Dependency("<=", less_or_equals[-1].version, less_or_equals[-1].package)]

        return strictest_conditions
