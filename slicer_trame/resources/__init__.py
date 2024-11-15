from pathlib import Path


def resources_path() -> Path:
    return Path(__file__).parent


def get_css_path() -> Path:
    return resources_path() / "slicer_trame.css"


def get_terminologies_path() -> Path:
    return resources_path() / "terminologies"
