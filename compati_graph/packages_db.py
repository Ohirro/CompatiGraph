import requests
import sqlite3
import gzip
import re
from io import BytesIO
from datetime import datetime, timedelta
from tqdm import tqdm

class DebianPackageImporter:
    def __init__(self, db_path, debian_url, force_reload=False):
        self.db_path = db_path
        self.url = debian_url
        self.table_name = self._generate_table_name(self.url)
        self.conn = sqlite3.connect(self.db_path)
        self._setup_database()
        need_reload = self._check_db_expiry() or force_reload or self._check_url_change()
        if need_reload:
            self._clear_database()
            self._setup_database()
            self.download_and_parse_packages_file(self.url)

    def _generate_table_name(self, url):
        # Удаляем протокол и заменяем недопустимые символы на подчеркивания
        name = re.sub(r'https?://', '', url)
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        return 'packages_' + name[:50]  # Обрезаем, чтобы имя не было слишком длинным

    def _setup_database(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS db_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP NOT NULL,
            url TEXT
        )
        """)
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_name TEXT NOT NULL,
            version TEXT NOT NULL,
            architecture TEXT,
            dependencies TEXT,
            description TEXT
        )
        """)
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_package_name ON {self.table_name}(package_name)")
        self.conn.commit()

    def _update_metadata_after_insert(self):
        cursor = self.conn.cursor()
        if cursor.execute("SELECT COUNT(*) FROM db_metadata").fetchone()[0] == 0:
            cursor.execute("INSERT INTO db_metadata (created_at, url) VALUES (?, ?)", (datetime.now(), self.url))
        else:
            cursor.execute("UPDATE db_metadata SET created_at = ?, url = ? WHERE id = (SELECT MAX(id) FROM db_metadata)", (datetime.now(), self.url))
        self.conn.commit()

    def _clear_database(self):
        cursor = self.conn.cursor()
        cursor.execute(f"DELETE FROM {self.table_name}")
        cursor.execute("DELETE FROM db_metadata")
        self.conn.commit()

    def _check_db_expiry(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT created_at FROM db_metadata ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        if result:
            created_at = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S.%f")
            return datetime.now() - created_at > timedelta(minutes=15)
        return False

    def _check_url_change(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT url FROM db_metadata ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        if not result or result[0] != self.url:
            return True
        return False

    def _bulk_insert_packages(self, packages):
        prepared_packages = []
        for pkg in packages:
            prepared_pkg = {
                'Package': pkg.get('Package', ''),
                'Version': pkg.get('Version', ''),
                'Architecture': pkg.get('Architecture', ''),
                'Depends': pkg.get('Depends', ''),
                'Description': pkg.get('Description', '')
            }
            prepared_packages.append(prepared_pkg)

        with self.conn:
            cursor = self.conn.cursor()
            cursor.executemany(f"""
            INSERT INTO {self.table_name} (package_name, version, architecture, dependencies, description)
            VALUES (:Package, :Version, :Architecture, :Depends, :Description)
            """, prepared_packages)

    def _download_with_progress(self, url):
        response = requests.get(url, stream=True)
        total_size_in_bytes = int(response.headers.get('content-length', 0))
        block_size = 1024
        progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
        content = BytesIO()
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            content.write(data)
        progress_bar.close()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            print("ERROR, something went wrong")
        content.seek(0)
        return content

    def download_and_parse_packages_file(self, url):
        content = self._download_with_progress(url)
        packages = []
        with gzip.open(content, 'rt') as f:
            package = {}
            for line in f:
                if line == '\n':
                    if package:
                        packages.append(package)
                        package = {}
                    continue
                key, value = line.split(':', 1)
                package[key.strip()] = value.strip()
            if package:
                packages.append(package)

        with tqdm(total=len(packages), desc="Inserting packages", unit="pkg") as progress_bar:
            self._bulk_insert_packages(packages)
            progress_bar.update(len(packages))
        self._update_metadata_after_insert()

    def force_reload(self):
        self._clear_database()
        self._setup_database()
        self.download_and_parse_packages_file(self.url)

    def close(self):
        self.conn.close()

class DebianPackageInfo(DebianPackageImporter):
    def __init__(self, db_path, debian_url, force_reload=False):
        super().__init__(db_path, debian_url, force_reload)

    def get_version(self, package_names):
        """Возвращает версии для указанных пакетов."""
        versions = {}
        with self.conn as conn:
            cursor = conn.cursor()
            for name in package_names:
                cursor.execute(f"SELECT version FROM {self.table_name} WHERE package_name = ?", (name,))
                result = cursor.fetchone()
                versions[name] = result[0] if result else None
        return versions

    def get_data(self, package_names):
        """Возвращает полные данные для указанных пакетов."""
        data = {}
        with self.conn as conn:
            cursor = conn.cursor()
            for name in package_names:
                cursor.execute(f"SELECT * FROM {self.table_name} WHERE package_name = ?", (name,))
                result = cursor.fetchone()
                if result:
                    data[name] = {
                        'id': result[0],
                        'package_name': result[1],
                        'version': result[2],
                        'architecture': result[3],
                        'dependencies': result[4],
                        'description': result[5]
                    }
                else:
                    data[name] = None
        return data

# Example usage
if __name__ == "__main__":
    importer = DebianPackageInfo('debian_packages.db', "http://deb.debian.org/debian/dists/stable/main/binary-amd64/Packages.gz")
    print(importer.get_data(["vim"]))
    importer.close()
