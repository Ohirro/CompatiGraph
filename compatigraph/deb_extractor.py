import subprocess
import tarfile
import os


#TODO refactor that garbagio

class DepsExtractor:
    def __init__(self, deb_path: str = None) -> None:
        self.deb_path = deb_path

    def extract_dependencies_from_deb(self):
        #TODO use context manager here
        subprocess.run(['ar', 'x', self.deb_path], check=True)
        control_archive_path = 'control.tar.gz'
        if not os.path.exists(control_archive_path):
            control_archive_path = 'control.tar.xz'
        #TODO  Could be a dict like struct
        if control_archive_path.endswith('.gz'):
            mode = 'r:gz'
        else:
            mode = 'r:xz'
        with tarfile.open(control_archive_path, mode) as tar:
            tar.extract("./control")
        
        dependencies = []
        with open('control', 'r', encoding="utf-8") as control_file:
            for line in control_file:
                if line.startswith('Depends:'):
                    dependencies = line.split(':', 1)[1].strip().split(', ')
                    break
                elif line.startswith('Recommends:'):
                    dependencies = line.split(':', 1)[1].strip().split(', ')
                    break
        #TODO rewrite that Garbage
        os.remove(control_archive_path)
        os.remove('control')
        os.remove('data.tar.xz')
        os.remove('debian-binary')
        
        return dependencies

