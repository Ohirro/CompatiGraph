import csv
from csv import writer as csv_writer
from pathlib import Path
from typing import Tuple, Dict, Any

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
            # TODO get line dependencies from DB
            line_from_db = ""
            self._deps = ""

    @property
    def solver_meta(self):
        if self._solver_meta is None:
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

    def get_deps_by_table(self, package, table, dh: DepHandler):
        res = {}
        line = [self.db_handler.get_dependencies(table, package)]
        added = set(package, )
        while line:
            a = line.pop()
            checked = dh.parse_dependencies_detailed(a, package)
            for pkg, dep in checked.items():
                if pkg not in added:
                    added.add(pkg)
                    new_line = self.db_handler.get_dependencies(table, pkg)
                    line.append(new_line)
                res = dh.merge_dependencies_detailed(res, checked)
        return res

    def solve(self) -> tuple[dict, dict[Any, dict[str, str]]]:
        """
        Solves the dependencies, checks them against all tables in the database,
        and prepares the results.

        Returns:
            A dictionary mapping each dependency to its analysis result, strictest conditions,
            and database check result.
        """
        # TODO
        dh = DepHandler()
        deps = {}
        for tb in self.db_handler.fetch_table_names():
            deps[tb] = self.get_deps_by_table(self._package[0], tb, dh)
        results = {key: {} for key in list(deps.keys())}

        for tb, val in deps.items():
            for key, value in val.items():
                if not (conflict := self.solver_meta.analyze_dependencies(value)):
                    confines = self.solver_meta.find_strictest_conditions(value)
                    results[tb][key] = {"status": "OK", "confines": confines}
                else:
                    results[tb][key] = {"status": "FAIL", "reason": f"Fail {conflict}"}

        db_check_results = {}
        for tb, val in deps.items():
            db_check_results[tb] = self.db_handler.check_dependencies_in_table(tb, val)

        return results, db_check_results

    def save_results_to_csv(self, name: str, results: dict[str, dict], db_res: dict[str, dict]):
        # Сохранение результатов анализа зависимостей
        with open(f"{name}_analysis.csv", "w", newline='') as csvfile:
            fieldnames = ['table', 'dependency', 'status', 'confines']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for table, dependencies in results.items():
                for dep, analysis in dependencies.items():
                    # Преобразование confines в строку для записи в CSV
                    confines_str = ', '.join([f"{op}: {', '.join([str(dep) for dep in deps])}" for op, deps in analysis['confines'].items()])
                    row = {'table': table, 'dependency': dep, 'status': analysis['status'], 'confines': confines_str}
                    writer.writerow(row)

        # Сохранение результатов проверки зависимостей в базе данных
        with open(f"{name}_db_check.csv", "w", newline='') as csvfile:
            fieldnames = ['table', 'dependency', 'result']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for table, dependencies in db_res.items():
                for dep, result in dependencies.items():
                    # Преобразование списка результатов в строку
                    result_str = '; '.join(result)
                    row = {'table': table, 'dependency': dep, 'result': result_str}
                    writer.writerow(row)
