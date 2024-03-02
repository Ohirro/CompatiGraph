from apt_worker import DepHandler, AptExecutor
from logic import LogicSolver

from pathlib import Path
from typing import Union


class Executor:
    def __init__(self, package: Union[str, Path] = None, verbose: bool = None) -> None:
        #TODO this is not a great way of handling of new object creation, could be slow.
        #TODO to think about lazy strategy.
        self.solver_meta = LogicSolver()
        self.dep_handel = DepHandler()
        apt_executor = AptExecutor()
        self.deps = apt_executor.get_dependencies(package)

    def solve(self):
        parsed_dependencies_detailed = DepHandler.parse_dependencies_detailed(self.deps)
        for key, value in parsed_dependencies_detailed.items():
            is_correct = self.solver_meta.analyze_dependencies(value)
            print(key,
                "OK: "+str(self.solver_meta.find_strictest_conditions(value)) 
                    if is_correct[0] 
                    else ("FAIL: ", is_correct[1]
                ))
