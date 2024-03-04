import argparse

from .executor import Executor


class CLI:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Deps analizer")
        self.parser.add_argument("input", help="Input filename or a package.")
        self.parser.add_argument("-o", "--output", help="Output file path", default="output.csv")
        self.parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode")

    def run(self):
        args = self.parser.parse_args()
        if args.verbose:
            print("Verbose mode activated.")
        runner = Executor(args.input)
        # TODO Add a print or show function.
        runner.solve()
