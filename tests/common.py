"""Define shared fixtures."""
# pylint: disable=redefined-outer-name, protected-access
import pathlib


def get_fixture_path(filename: str) -> pathlib.Path:
    """Get path of fixture."""
    return pathlib.Path(__file__).parent.joinpath("fixtures", filename)


def load_fixture(filename):
    """Load a fixture."""
    return get_fixture_path(filename).read_text()
