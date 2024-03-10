from subprocess import Popen
import subprocess
from contextlib import contextmanager


class UnknownPkgException(Exception):
    ...


@contextmanager
def managed_popen(*args, **kwargs):
    process = Popen(*args, **kwargs)
    try:
        yield process
    finally:
        process.terminate()
        process.wait()

def find_the_pkg(pkg):
    with managed_popen(['apt', 'info', pkg], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        out, _ = process.communicate()
        if not out:
            raise UnknownPkgException(f"Unable to find a {pkg}") from None