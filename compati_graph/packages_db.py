import requests
import sqlite3
import gzip
from io import BytesIO
from tqdm import tqdm

class DebianPackageImporter:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._setup_database()

    def _setup_database(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS debian_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_name TEXT NOT NULL,
            version TEXT NOT NULL,
            architecture TEXT,
            dependencies TEXT,
            description TEXT
        )
        """)

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
            cursor.executemany("""
            INSERT INTO debian_packages (package_name, version, architecture, dependencies, description)
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

    def close(self):
        self.conn.close()

# Example usage
if __name__ == "__main__":
    importer = DebianPackageImporter('debian_packages.db')
    url = "http://deb.debian.org/debian/dists/stable/main/binary-amd64/Packages.gz"
    importer.download_and_parse_packages_file(url)
    importer.close()
