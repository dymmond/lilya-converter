"""Executable module entrypoint for `python -m lilya_converter`."""

from lilya_converter.cli import app


def run() -> None:
    """Run the root Sayer application."""
    app()


if __name__ == "__main__":
    run()
