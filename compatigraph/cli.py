import argparse
import sys

from compatigraph.executor import Executor
from compatigraph.helper import UnknownPkgException, find_the_pkg


class CLI:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Deps analizer")
        self.parser.add_argument(
            "input",
            help="Input filename or a package.",
        )
        self.parser.add_argument(
            "-s",
            "--source",
            help="which source to use, could be a link or source.",
            default="/etc/apt/",
        )
        self.parser.add_argument(
            "-o",
            "--output",
            help="Output file path",
            default="output.csv",
        )
        self.parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Verbose mode",
        )

    def run(self):
        args = self.parser.parse_args()
        if args.verbose:
            print("Verbose mode activated.")

        if "=" in args.input:
            name=args.input.split("=")[0]
            version=args.input.split("=")[1]
        try:
            find_the_pkg(args.input)
        except UnknownPkgException as e:
            sys.stderr.write(f"Error: {e.__class__.__name__}: {e}\n")
            sys.exit(0)
        runner = Executor(package=(name, version), source=args.source)
        results = runner.solve()
        runner.print_results(results)
        runner.save_results_to_csv(results)
