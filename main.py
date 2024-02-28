from apt_worker import DepHandler, AptExecutor
from logic import LogicSolver


dep_handel = DepHandler()
solver_meta = LogicSolver()
apt_executor = AptExecutor()

deps = apt_executor.get_dependencies("vim")

parsed_dependencies_detailed = DepHandler.parse_dependencies_detailed(deps)

for key, value in parsed_dependencies_detailed.items():
    is_correct = solver_meta.analyze_dependencies(value)
    print(key, "OK: "+str(solver_meta.find_strictest_conditions(value)) if is_correct[0] else ("FAIL: ", is_correct[1]))
