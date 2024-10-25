import argparse
import importlib
from upath import UPath


def main():
    parser = argparse.ArgumentParser(
        description="The upcat utility reads the content from paths sequentially, writing them to the standard output."
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s " + importlib.metadata.version("upcat"),
    )

    parser.add_argument("path", nargs="+", help="path to content")

    args = parser.parse_args()

    for path in args.path:
        print(UPath(path).read_text())


if __name__ == "__main__":
    main()
