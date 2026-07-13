"""Entry point for ``python -m cozer`` — launches the PySide6 GUI."""
import sys


def main(argv=None):
    from cozer.app.main import run
    return run(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    sys.exit(main())
