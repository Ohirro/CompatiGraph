import gzip
import lzma
import re
import subprocess
from contextlib import contextmanager
from io import BytesIO
from subprocess import Popen

import requests
import tqdm


class UnknownPkgException(Exception): ...


@contextmanager
def managed_popen(*args, **kwargs):
    process = Popen(*args, **kwargs)
    try:
        yield process
    finally:
        process.terminate()
        process.wait()


def find_the_pkg(pkg):
    with managed_popen(["apt", "info", pkg], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        out, _ = process.communicate()
        if not out:
            raise UnknownPkgException(f"Unable to find a {pkg}") from None


class GenericHelpers:
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

    def download_and_packages_file(self, url: str = None):
        content = self._download_with_progress(url)
        # TODO add other formats
        if url.endswith(".gz"):
            with gzip.open(content, "rt") as f:
                return f.read()
        elif url.endswith(".xz"):
            with lzma.open(content, "rt") as f:
                return f.read()
        else:
            raise ValueError("Unsupported file format")

    @staticmethod
    def beautify_name(name_raw: str, additional_str: str) -> str:
        if additional_str not in ["remote", "local"]:
            raise ValueError(f"Impossible type location {additional_str}")
        if "http" in name_raw:
            rm_protocol = re.sub(r"https?://", "", name_raw)
            name_raw = re.sub(r"[^a-zA-Z0-9_]", "_", rm_protocol)
        for fragment in name_raw.split("_"):
            if "-" in fragment and len(fragment.split("-")) >= 2 and not "debian" in fragment:
                return additional_str + fragment
        return additional_str + name_raw.capitalize().replace(".", "").replace("deb", "")
