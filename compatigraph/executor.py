from pathlib import Path
from typing import Union

from compatigraph.apt_worker import AptExecutor, DepHandler
from compatigraph.logic import LogicSolver
from compatigraph.packages_db import DebianPackageInfo


class Executor:
    def __init__(self, package: Union[str, Path] = None, verbose: bool = None) -> None:
        self._package = package
        self._verbose = verbose
        self._solver_meta = None
        self._dep_handel = None
        self._apt_executor = None
        self._deps = None
        self._db_info = None

    @property
    def solver_meta(self):
        if self._solver_meta is None:
            self._solver_meta = LogicSolver()
        return self._solver_meta

    @property
    def dep_handel(self):
        if self._dep_handel is None:
            self._dep_handel = DepHandler()
        return self._dep_handel

    @property
    def apt_executor(self):
        if self._apt_executor is None:
            self._apt_executor = AptExecutor()
        return self._apt_executor

    @property
    def deps(self):
        if self._deps is None:
            self._deps = self.apt_executor.get_dependencies(self._package)
        return self._deps

    @property
    def db_info(self):
        if self._db_info is None:
            self._db_info = DebianPackageInfo("debian_packages.db")
        return self._db_info

    def solve(self):
        """
        Solves the dependencies, checks them against all tables in the database,
        and prepares the results.

        Returns:
            A dictionary mapping each dependency to its analysis result, strictest conditions,
            and database check result.
        """
        parsed_dependencies_detailed = self.dep_handel.parse_dependencies_detailed(self.deps)
        results = {}

        for key, value in parsed_dependencies_detailed.items():
            analysis_result = self.solver_meta.analyze_dependencies(value)
            if analysis_result:
                confines = self.solver_meta.find_strictest_conditions(value)
                results[key] = {'status': 'OK', 'confines': confines}
            else:
                results[key] = {'status': 'FAIL', 'reason': analysis_result[1]}

        # Perform the database check as part of the solving process
        confines_map = {key: value['confines'] for key, value in results.items() if value['status'] == 'OK'}
        db_check_results = self.db_info.check_dependencies_in_all_tables(confines_map)
        
        # Update results with database check information
        for key in confines_map.keys():
            results[key]['db_check'] = db_check_results.get(key, 'Not found')

        return results
    def print_results(self, results):
        """
        Prints the results of the dependency analysis, including the database checks, in a table format.

        Args:
            results: The results dictionary from the solve function.
        """
        header = ["Dependency", "Status", "Confines", "DB Check"]
        print(f"{header[0]:<30} {header[1]:<10} {header[2]:<50} {header[3]:<20}")
        print("-" * 110)  # Adjust the number based on the total width of the table

        for key, value in results.items():
            status = str(value['status'])
            # Ensure confines and db_check are converted to string properly
            confines = str(value.get('confines', 'N/A')) if isinstance(value.get('confines'), (str, int)) else 'Complex Data'
            db_check = str(value.get('db_check', 'N/A')) if isinstance(value.get('db_check'), (str, int)) else 'Complex Data'
            print(f"{key:<30} {status:<10} {confines:<50} {db_check:<20}")
