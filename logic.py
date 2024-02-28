from debian.debian_support import Version
from apt_worker import Dependency

class LogicSolver:

    def __init__(self) -> None:
        ...

    def analyze_dependencies(self, dependencies):
        equals = dependencies.get('=', [])
        greater_or_equals = dependencies.get('>=', [])
        less_or_equals = dependencies.get('<=', [])
        strictly_greater = dependencies.get('>>', [])
        strictly_less = dependencies.get('<<', [])
        conflicts = []

        # 1. Проверка "=" зависимостей на идентичность версий
        if len(set(dep.version for dep in equals)) > 1:
            conflicts.append(('=', equals))

        # 2. Сравнение ">=" и "<="
        if greater_or_equals and less_or_equals:
            if Version(greater_or_equals[0].version) > Version(less_or_equals[-1].version):
                conflicts.append(('>= <=', [greater_or_equals[0], less_or_equals[-1]]))

        # 3. Сравнение ">>" и "<<"
        if strictly_greater and strictly_less:
            if Version(strictly_greater[0].version) <= Version(strictly_less[-1].version):
                conflicts.append(('>> <<', [strictly_greater[0], strictly_less[-1]]))

        # 4. Совместимость "=" с другими операторами
        for eq_dep in equals:
            # Сравнение "=" с ">=", "<<", ">>", и "<="
            self.check_compatibility_with_equals(eq_dep, greater_or_equals, less_or_equals, strictly_greater, strictly_less, conflicts)

        # 5. Сравнение ">=" и ">>"
        if greater_or_equals and strictly_greater:
            if Version(greater_or_equals[0].version) > Version(strictly_greater[0].version):
                conflicts.append(('>= >>', [greater_or_equals[0], strictly_greater[0]]))

        # 6. Сравнение "<=" и "<<"
        if less_or_equals and strictly_less:
            if Version(less_or_equals[-1].version) < Version(strictly_less[-1].version):
                conflicts.append(('<= <<', [less_or_equals[-1], strictly_less[-1]]))

        # 7. Сравнение ">=" и "<<"
        if greater_or_equals and strictly_less:
            if Version(greater_or_equals[0].version) <= Version(strictly_less[-1].version):
                conflicts.append(('>= <<', [greater_or_equals[0], strictly_less[-1]]))

        # 8. Сравнение "<=" и ">>"
        if less_or_equals and strictly_greater:
            if Version(less_or_equals[-1].version) <= Version(strictly_greater[0].version):
                conflicts.append(('<= >>', [less_or_equals[-1], strictly_greater[0]]))

        # Возвращаем все найденные конфликты
        if conflicts:
            return False, conflicts

        # Все проверки пройдены, зависимости корректны
        return True, None

    @staticmethod
    def check_compatibility_with_equals(eq_dep, greater_or_equals, less_or_equals, strictly_greater, strictly_less, conflicts):
        eq_version = Version(eq_dep.version)
        # "=" с ">="
        if greater_or_equals and eq_version < Version(greater_or_equals[0].version):
            conflicts.append(('= >=', [eq_dep, greater_or_equals[0]]))
        # "=" с "<="
        if less_or_equals and eq_version > Version(less_or_equals[-1].version):
            conflicts.append(('= <=', [eq_dep, less_or_equals[-1]]))
        # "=" с ">>"
        if strictly_greater and eq_version <= Version(strictly_greater[0].version):
            conflicts.append(('= >>', [eq_dep, strictly_greater[0]]))
        # "=" с "<<"
        if strictly_less and eq_version >= Version(strictly_less[-1].version):
            conflicts.append(('= <<', [eq_dep, strictly_less[-1]]))


    @staticmethod
    def find_strictest_conditions(dependencies):
        equals = dependencies.get('=', [])
        greater_or_equals = dependencies.get('>=', [])
        less_or_equals = dependencies.get('<=', [])
        strictly_greater = dependencies.get('>>', [])
        strictly_less = dependencies.get('<<', [])

        strictest_conditions = {}

        # Условие для "="
        if equals:
            versions = set(dep.version for dep in equals)
            if len(versions) == 1:
                strictest_conditions['='] = [Dependency('=', versions.pop(), None)]
            else:
                raise ValueError("Conflicting '=' conditions")

        # Максимальное условие для ">"
        if strictly_greater:
            max_version = max(strictly_greater, key=lambda dep: Version(dep.version)).version
            strictest_conditions['>>'] = [Dependency('>>', max_version, None)]
        elif greater_or_equals:  # Используем ">=" если нет ">>"
            max_version = max(greater_or_equals, key=lambda dep: Version(dep.version)).version
            strictest_conditions['>='] = [Dependency('>=', max_version, None)]

        # Минимальное условие для "<"
        if strictly_less:
            min_version = min(strictly_less, key=lambda dep: Version(dep.version)).version
            strictest_conditions['<<'] = [Dependency('<<', min_version, None)]
        elif less_or_equals:  # Используем "<=" если нет "<<"
            min_version = min(less_or_equals, key=lambda dep: Version(dep.version)).version
            strictest_conditions['<='] = [Dependency('<=', min_version, None)]

        return strictest_conditions
