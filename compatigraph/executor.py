from pathlib import Path
from typing import Union

from compatigraph.apt_worker import AptExecutor, DepHandler
from compatigraph.logic import LogicSolver
from compatigraph.packages_db import DebianPackageInfo


class Executor:
    def __init__(self, package: Union[str, Path] = None, verbose: bool = None) -> None:
        # TODO this is not a great way of handling of new object creation, could be slow.
        # TODO to think about lazy strategy.
        self.solver_meta = LogicSolver()
        self.dep_handel = DepHandler()
        apt_executor = AptExecutor()
        self.deps = apt_executor.get_dependencies(package)
        self.db_info = DebianPackageInfo("debian_packages.db")

    def solve(self):
        parsed_dependencies_detailed = DepHandler.parse_dependencies_detailed(self.deps)

        confines_map = {}
        for key, value in parsed_dependencies_detailed.items():
            is_correct = self.solver_meta.analyze_dependencies(value)
            if is_correct:
                confines = self.solver_meta.find_strictest_conditions(value)
                print(key, "OK: " + str(confines))
                confines_map[key] = confines
            else:
                print(key, "FAIL ", is_correct[1])
        print(self.db_info.check_dependencies_in_all_tables(confines_map))
