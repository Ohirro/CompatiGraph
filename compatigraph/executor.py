from pathlib import Path

from compatigraph.apt_worker import AptExecutor, DepHandler
from compatigraph.logic import LogicSolver
from compatigraph.packages_db import DebianPackageInfo, DebianPackageImporter
from compatigraph.sources import SourceHandler
from csv import writer as csv_writer


class Executor:
    def __init__(
        self,
        package: str | Path = None,
        verbose: bool = None,
        source: str | Path = None,
    ) -> None:
        self._package = package
        self._verbose = verbose
        self.source = source
        if source is None:
            self.source = Path("/etc/apt")
        self._solver_meta = None
        self._dep_handel = None
        self._apt_executor = None
        self._deps = None
        self._db_init = None
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

    @property
    def sources_links(self):
        sh = SourceHandler(self.source)
        links = sh.system_links()
        return links

    def db_init(self):
        if self._db_init is None:
            self._db_init = DebianPackageImporter("debian_packages.db", debian_urls=self.sources_links)
            self._db_init.close()
        return self._db_init

    def solve(self) -> dict[str, tuple[str, str]]:
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
            # analysis_result = self.solver_meta.analyze_dependencies(value)
            if not (conflict := self.solver_meta.analyze_dependencies(value)):
                confines = self.solver_meta.find_strictest_conditions(value)
                results[key] = {"status": "OK", "confines": confines}
            else:
                results[key] = {"status": "FAIL", "reason": f"Fail {conflict}"}

        # Perform the database check as part of the solving process
        confines_map = {key: value["confines"] for key, value in results.items() if value["status"] == "OK"}
        self.db_init()
        db_check_results = self.db_info.check_dependencies_in_all_tables(confines_map)

        # Update results with database check information
        for key in confines_map.keys():
            for db, db_data in db_check_results.items():
                results[key][db] = db_data.get(key, "OK")

        return results

    def print_results(self, results: dict[str, tuple[str, str]]):
        """
        Prints the results of the dependency analysis, including the database checks, in a table format.

        :results: dict[str, tuple[str, str]] The results dictionary from the solve function.
        """
        db_names = set()
        for key, value in results.items():
            for db in value.keys():
                if db not in ("status", "confines"):
                    db_names.add(db)

        db_names = sorted(list(db_names))  # Сортировка имен баз данных для последовательного отображения

        # Определяем ширину колонки на основе самого длинного имени базы данных
        max_db_name_length = max(len(db) for db in db_names) + 5  # Добавляем небольшой отступ

        header = ["Dependency", "Status", "Confines"] + db_names
        header_format = "{:<30} {:<10} {:<50} " + " ".join([f"{{:<{max_db_name_length}}}" for _ in db_names])
        print(header_format.format(*header))

        print("-" * (90 + max_db_name_length * len(db_names)))

        for key, value in results.items():
            status = str(value["status"])
            confines = self.format_confines(value.get("confines"))

            # Сбор данных проверки для каждой базы данных
            db_checks = [str(value.get(db_name, "N/A")) for db_name in db_names]

            row_format = "{:<30} {:<10} {:<50} " + " ".join([f"{{:<{max_db_name_length}}}" for _ in db_names])
            print(row_format.format(key, status, confines, *db_checks))

    @staticmethod
    def format_confines(confines):
        if not confines or not isinstance(confines, dict):
            return "Any"

        constraints = []
        for operator, dependencies in confines.items():
            for dep in dependencies:
                constraints.append(f"{operator} {dep.version}")

        return ", ".join(constraints) if constraints else "None"

    def save_results_to_csv(self, results: dict[str, tuple[str, str]]):
        db_names = set()
        for key, value in results.items():
            for db in value.keys():
                if db not in ("status", "confines"):
                    db_names.add(db)

        db_names = sorted(list(db_names))

        with open('dependency_analysis_results.csv', mode='w', newline='') as file:
            writer = csv_writer(file)

            headers = ["Dependency", "Status", "Confines"] + db_names
            writer.writerow(headers)

            for key, value in results.items():
                status = str(value["status"])
                confines = self.format_confines(value.get("confines"))
                db_checks = [str(value.get(db_name, "N/A")) for db_name in db_names]
                row = [key, status, confines] + db_checks
                writer.writerow(row)
