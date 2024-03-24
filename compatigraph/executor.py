from csv import writer as csv_writer
from pathlib import Path

from compatigraph.apt_worker import DepHandler
from compatigraph.db_handler import DBHandler
from compatigraph.logic import LogicSolver
from compatigraph.packages_db import DebianPackageExtractor
from compatigraph.sources import SourceHandler


class Executor:
    def __init__(
        self,
        package: tuple[str | Path, str] = None,
        verbose: bool = None,
        source: str | Path = None,
    ) -> None:
        self._package = package
        self._verbose = verbose
        self.source = source
        if source is None:
            self.source = Path("/etc/apt")
        self._solver_meta = None
        self._dep_handler = None
        self._db_handler = None
        self._db_init = None
        self._deps = None

    @property
    def deps(self):
        if not self.deps:
            #TODO get line dependencies from DB
            line_from_db = ""
            self._deps = ""

    @property
    def solver_meta(self):
        if self._solver_meta:
            self._solver_meta = LogicSolver()
        return self._solver_meta

    @property
    def dep_handel(self):
        if self._dep_handler is None:
            self._dep_handler = DepHandler()
        return self._dep_handler

    @property
    def db_handler(self):
        if self._db_handler is None:
            self._db_handler = DBHandler(".packages_db.db")
        return self._db_handler

    @property
    def sources_links(self):
        sh = SourceHandler(self.source)
        links = sh.system_links()
        return links


    def prepare(self):
        packages = DebianPackageExtractor(self.sources_links)
        packages = packages.convert_repos()
        self.db_handler.make_dbs(list(packages.keys()))
        self.db_handler.insert_packages(packages)

    def solve(self) -> dict[str, tuple[str, str]]:
        """
        Solves the dependencies, checks them against all tables in the database,
        and prepares the results.

        Returns:
            A dictionary mapping each dependency to its analysis result, strictest conditions,
            and database check result.
        """
        # TODO
        dh = DepHandler()
        deps_line_from_db = ""
        print(self.db_handler.get_dependencies("local", "bind9"))
        sparsed_dependencies_detailed= dh.parse_dependencies_detailed(deps_line=deps_line_from_db, package_name=self._package[0])

        parsed_dependencies_detailed = self.dep_handel.parse_dependencies_detailed()
        results = {}

        for key, value in parsed_dependencies_detailed.items():
            if not (conflict := self.solver_meta.analyze_dependencies(value)):
                confines = self.solver_meta.find_strictest_conditions(value)
                results[key] = {"status": "OK", "confines": confines}
            else:
                results[key] = {"status": "FAIL", "reason": f"Fail {conflict}"}

        # Perform the database check as part of the solving process
        confines_map = {key: value["confines"] for key, value in results.items() if value["status"] == "OK"}
        db_check_results = self.db_handler.check_dependencies_in_all_tables(confines_map)

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

        with open("dependency_analysis_results.csv", mode="w", newline="", encoding="utf8") as file:
            writer = csv_writer(file)

            headers = ["Dependency", "Status", "Confines"] + db_names
            writer.writerow(headers)

            for key, value in results.items():
                status = str(value["status"])
                confines = self.format_confines(value.get("confines"))
                db_checks = [str(value.get(db_name, "N/A")) for db_name in db_names]
                row = [key, status, confines] + db_checks
                writer.writerow(row)
