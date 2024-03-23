import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import tqdm


class DBHandler:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

    def insert_packages(self, converted_repos: dict[str, list[dict[str, str]]]):
        for repo, packages in converted_repos.items():
            with tqdm(total=len(packages), desc="Inserting packages", unit="pkg") as progress_bar:
                self._bulk_insert_packages(repo, packages)
                progress_bar.update(len(packages))
            self._update_metadata_after_insert(repo)

    def close(self):
        self.conn.close()

    def make_dbs(self, tables_names: list[str]):
        self._setup_database(tables_names)
        # if self._check_db_expiry() or self._check_url_change(tables_names):
        #     self._setup_database(tables_names)

    def _setup_database(self, tables_names: list[str]):
        cursor = self.conn.cursor()
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS db_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP NOT NULL,
            url TEXT
        )
        """
        )
        for table_name in tables_names:
            cursor.execute(
                f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_name TEXT NOT NULL,
                version TEXT NOT NULL,
                architecture TEXT,
                dependencies TEXT,
                description TEXT
            )
            """
            )
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS idx_package_name_version ON {table_name}(package_name, version)"
            )
        self.conn.commit()

    def _update_metadata_after_insert(self, table_name: str):
        cursor = self.conn.cursor()
        if cursor.execute(f"SELECT COUNT(*) FROM db_metadata where url = '{table_name}'").fetchone()[0] == 0:
            cursor.execute("INSERT INTO db_metadata (created_at, url) VALUES (?, ?)", (datetime.now(), table_name))
        else:
            cursor.execute(
                "UPDATE db_metadata SET created_at = ?, url = ? WHERE url = '{table_name}'",
                (datetime.now(), table_name),
            )
        self.conn.commit()

    def _check_db_expiry(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT created_at FROM db_metadata ORDER BY id DESC LIMIT 1")
        if result := cursor.fetchone():
            created_at = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S.%f")
            return datetime.now() - created_at > timedelta(minutes=15)
        return False

    def _check_url_change(self, table_name):
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT url FROM db_metadata WHERE url = '{table_name}'")
        if not cursor.fetchone():
            return True
        return False

    def _bulk_insert_packages(self, table_name: str, packages: list[dict[str, str]]):
        prepared_packages = []
        for pkg in packages:
            prepared_pkg = {
                "Package": pkg.get("Package", ""),
                "Version": pkg.get("Version", ""),
                "Architecture": pkg.get("Architecture", ""),
                "Depends": pkg.get("Depends", ""),
                "Description": pkg.get("Description", ""),
            }
            prepared_packages.append(prepared_pkg)

        with self.conn:
            cursor = self.conn.cursor()
            cursor.executemany(
                f"""
            INSERT INTO {table_name} (package_name, version, architecture, dependencies, description)
            VALUES (:Package, :Version, :Architecture, :Depends, :Description)
            """,
                prepared_packages,
            )

    # TODO call after dbload
    def _fetch_table_names(self):
        cursor = self.conn.cursor()
        # TODO переделать, чтобы явно сличать структуру
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != db_metadata",
        )
        rows = cursor.fetchall()
        self.tables = [row[0] for row in rows]

    def get_version(self, table_name: str, package: str) -> str:
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT version FROM {table_name} WHERE package_name = ?", (package,))
        return cursor.fetchone()

    def check_dependencies_in_table(
        self,
        table_name: str,
        dependencies: dict[str, str],
    ) -> dict[str, str]:
        """
        Проверяет зависимости в конкретной таблице.

        table_name: Имя таблицы для проверки.
        dependencies: Словарь зависимостей для проверки.
        return: Список ошибок.
        """
        errors = {}

        for package, deps in dependencies.items():
            for _, dep_list in deps.items():
                for dep in dep_list:
                    err_str = None
                    if not (result := self.get_version(table_name, package)):
                        err_str = f"not found {package} need {dep.operator} {dep.version}"
                    elif not dep.is_satisfied_by(result[0]):
                        err_str = f"{package} dependency unsatisfied: {result[0]}{dep.operator}{dep.version}"
                    if err_str:
                        errors[package] = errors.get(package, [])
                        errors[package].append(err_str)

        return errors

    def check_dependencies_in_all_tables(self, dependencies: dict[str, str]) -> dict[str, str]:
        """
        Проверяет зависимости во всех таблицах.

        dependencies: Словарь зависимостей для проверки.
        return: Словарь ошибок по таблицам.
        """
        all_errors = {}
        for table in self.tables:
            errors = self.check_dependencies_in_table(table, dependencies)
            all_errors[table] = errors

        return all_errors
