import gzip
import re
import lzma
import sqlite3
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import requests
from tqdm import tqdm

Metadata = "db_metadata"


class DebianPackageImporter:
    def __init__(self, db_path: str | Path, debian_urls: list[str] = None, force_reload=True):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        for url in debian_urls:
            self.table_name = self._generate_table_name(url)
            self._setup_database()
            if self._check_db_expiry() or force_reload or self._check_url_change():
                self.download_and_parse_packages_file(url)
                self._clear_database()
                self._setup_database()

    def _generate_table_name(self, url: str = None):
        # Удаляем протокол и заменяем недопустимые символы на подчеркивания
        name = re.sub(r"https?://", "", url)
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        return "packages_" + name[:50]  # Обрезаем, чтобы имя не было слишком длинным

    def _setup_database(self):
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
        cursor.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
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
            f"CREATE INDEX IF NOT EXISTS idx_package_name_version ON {self.table_name}(package_name, version)"
        )
        self.conn.commit()

    def _update_metadata_after_insert(self):
        cursor = self.conn.cursor()
        if cursor.execute(f"SELECT COUNT(*) FROM db_metadata where url = '{self.table_name}'").fetchone()[0] == 0:
            cursor.execute("INSERT INTO db_metadata (created_at, url) VALUES (?, ?)", (datetime.now(), self.table_name))
        else:
            cursor.execute(
                "UPDATE db_metadata SET created_at = ?, url = ? WHERE url = '{self.table_name}'",
                (datetime.now(), self.table_name),
            )
        self.conn.commit()

    def _clear_database(self):
        cursor = self.conn.cursor()
        cursor.execute(f"DELETE FROM {self.table_name}")
        cursor.execute(f"DELETE FROM db_metadata where url = '{self.table_name}'")
        self.conn.commit()

    def _check_db_expiry(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT created_at FROM db_metadata ORDER BY id DESC LIMIT 1")
        if result := cursor.fetchone():
            created_at = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S.%f")
            return datetime.now() - created_at > timedelta(minutes=15)
        return False

    def _check_url_change(self):
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT url FROM db_metadata WHERE url = '{self.table_name}'")
        if not cursor.fetchone():
            return True
        return False

    def _bulk_insert_packages(self, packages):
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
            INSERT INTO {self.table_name} (package_name, version, architecture, dependencies, description)
            VALUES (:Package, :Version, :Architecture, :Depends, :Description)
            """,
                prepared_packages,
            )

    def _download_with_progress(self, url: str = None):
        response = requests.get(url, stream=True, timeout=90)
        total_size_in_bytes = int(response.headers.get("content-length", 0))
        block_size = 1024
        progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)
        content = BytesIO()
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            content.write(data)
        progress_bar.close()
        if set([total_size_in_bytes, progress_bar.n]) == set([0]):
            print("ERROR, something went wrong")
        content.seek(0)
        return content

    def download_and_parse_packages_file(self, url: str = None):
        # TODO to think about simplification
        content = self._download_with_progress(url)
        packages = []

        if url.endswith(".gz"):
            with gzip.open(content, "rt") as f:
                package = {}
                for line in f:
                    if line == "\n":
                        if package:
                            packages.append(package)
                            package = {}
                        continue
                    key, value = line.split(":", 1)
                    package[key.strip()] = value.strip()
                if package:
                    packages.append(package)
        elif url.endswith(".xz"):
            with lzma.open(content, "rt") as f:
                package = {}
                for line in f:
                    if line == "\n":
                        if package:
                            packages.append(package)
                            package = {}
                        continue
                    key, value = line.split(":", 1)
                    package[key.strip()] = value.strip()
                if package:
                    packages.append(package)
        else:
            raise ValueError("Unsupported file format")

        with tqdm(total=len(packages), desc="Inserting packages", unit="pkg") as progress_bar:
            self._bulk_insert_packages(packages)
            progress_bar.update(len(packages))
        self._update_metadata_after_insert()

    def force_reload(self, url: str = None):
        self._clear_database()
        self._setup_database()
        self.download_and_parse_packages_file(url)

    def close(self):
        self.conn.close()


class DebianPackageInfo:
    def __init__(self, db_path: str | Path = None):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.tables = []
        self._fetch_table_names()

    def _fetch_table_names(self):
        cursor = self.conn.cursor()
        # TODO переделать, чтобы явно сличать структуру
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != ?", (Metadata,)
        )
        rows = cursor.fetchall()
        self.tables = [row[0] for row in rows]

    def check_dependencies_in_table(self, table_name, dependencies):
        """
        Проверяет зависимости в конкретной таблице.

        table_name: Имя таблицы для проверки.
        dependencies: Словарь зависимостей для проверки.
        return: Список ошибок.
        """
        errors = {}
        cursor = self.conn.cursor()

        for package, deps in dependencies.items():
            for _, dep_list in deps.items():
                for dep in dep_list:
                    cursor.execute(f"SELECT version FROM {table_name} WHERE package_name = ?", (package,))
                    result = cursor.fetchone()
                    err_str = None
                    if not result:
                        err_str = f"not found {package} need {dep.operator} {dep.version}"
                    elif not dep.is_satisfied_by(result[0]):
                        err_str = f"{package} dependency unsatisfied: {result[0]}{dep.operator}{dep.version}"
                    if err_str:
                        errors[package] = errors.get(package, [])
                        errors[package].append(err_str)

        return errors

    def check_dependencies_in_all_tables(self, dependencies):
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
