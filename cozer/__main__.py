"""Entry point for ``python -m cozer``.

The graphical application is introduced in Phase 5 (see ``MAINTENANCE_PLAN.md``).
Until then this is a placeholder so the entry point exists and is testable.
"""
import sys


def main(argv=None):
    print(
        "cozer (new Python 3 implementation): the GUI arrives in Phase 5. "
        "The headless core is under active development."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
