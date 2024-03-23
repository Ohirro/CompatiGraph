from compatigraph.apt_worker import DepHandler, RepositoryFileHandler
from compatigraph.helper import GenericHelpers


class DebianPackageExtractor:
    def __init__(
        self,
        debian_urls: list[str] = None,
    ) -> None:
        print(debian_urls)
        self.debian_urls = debian_urls

    @staticmethod
    def get_packages_from_list(file_handle: str) -> list[dict[str, str]]:
        """
        Parses packages from an open file handle. Each package is separated by a blank line,
        and each line within a package contains a key-value pair separated by a colon.

        :param file_handle: An open file handle to read the packages from.
        :return: A list of dictionaries, where each dictionary represents a package.
        """
        packages = []
        package = {}
        for line in file_handle:
            if line == "\n":
                if package:
                    packages.append(package)
                    package = {}
                continue
            key, value = line.split(":", 1)
            package[key.strip()] = value.strip()
        if package:
            packages.append(package)
        return packages

    def convert_repos(self) -> dict[str, list[dict[str, str]]]:
        converted_repos = {}
        for repo in RepositoryFileHandler.extract_and_read_files():
            repo_name = GenericHelpers.beautify_name(repo[0], "local")
            repo_data = self.get_packages_from_list(repo[1])
            converted_repos[repo_name] = repo_data
        for url in self.debian_urls:
            # TODO use asyncio
            repo_name = GenericHelpers.beautify_name(url, "remote")
            repo_data = self.get_packages_from_list(GenericHelpers.download_and_packages_file(url))
            converted_repos[repo_name] = repo_data
        return converted_repos
