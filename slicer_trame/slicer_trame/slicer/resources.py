from pathlib import Path


def get_resources_folder() -> Path:
    return Path(__file__).parent.joinpath("../../resources").resolve()


def get_css_path() -> Path:
    return get_resources_folder() / "slicer_trame.css"
