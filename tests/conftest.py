import asyncio
from pathlib import Path

import pytest
from trame.app import get_server
from trame_server.utils.asynchronous import create_task
from vtkmodules.vtkMRMLCore import (
    vtkMRMLModelNode,
    vtkMRMLModelStorageNode,
    vtkMRMLVolumeArchetypeStorageNode,
)

from slicer_trame.core import SlicerApp
from slicer_trame.views import DirectRendering, SliceView, ThreeDView


@pytest.fixture
def a_slicer_app():
    return SlicerApp()


@pytest.fixture
def a_threed_view(a_slicer_app, render_interactive):
    three_d_view = ThreeDView(
        a_slicer_app.scene,
        a_slicer_app.app_logic,
        "ThreeD",
        scheduled_render_strategy=DirectRendering(),
    )
    if render_interactive:
        three_d_view.render_window().ShowWindowOn()
    three_d_view.interactor().UpdateSize(400, 300)
    yield three_d_view
    three_d_view.finalize()


@pytest.fixture
def a_slice_view(a_slicer_app, render_interactive):
    view = SliceView(
        a_slicer_app.scene,
        a_slicer_app.app_logic,
        "Red",
        scheduled_render_strategy=DirectRendering(),
    )
    if render_interactive:
        view.render_window().ShowWindowOn()
    return view


@pytest.fixture()
def a_data_folder():
    return Path(__file__).parent / "data"


@pytest.fixture()
def a_nrrd_volume_file_path(a_data_folder) -> Path:
    return a_data_folder.joinpath("mr_head.nrrd")


@pytest.fixture()
def a_nifti_volume_file_path(a_data_folder) -> Path:
    return a_data_folder.joinpath("mr_head.nii.gz")


@pytest.fixture()
def ct_chest_dcm_volume_file_paths(a_data_folder) -> list[Path]:
    return list(a_data_folder.joinpath("ct_chest_dcm").glob("*.dcm"))


@pytest.fixture()
def mr_head_dcm_volume_file_paths(a_data_folder) -> list[Path]:
    return list(a_data_folder.joinpath("mr_head_dcm").glob("*.dcm"))


@pytest.fixture()
def a_model_file_path(a_data_folder) -> Path:
    return a_data_folder.joinpath("model.stl")


@pytest.fixture()
def a_segmentation_stl_file_path(a_data_folder) -> Path:
    return a_data_folder.joinpath("segmentation.stl")


@pytest.fixture()
def a_segmentation_nifti_file_path(a_data_folder) -> Path:
    return a_data_folder.joinpath("segmentation.nii.gz")


@pytest.fixture
def a_model_node(a_slicer_app, a_model_file_path):
    return load_model_node(
        a_model_file_path.as_posix(),
        a_slicer_app,
    )


def load_model_node(file_path, a_slicer_app):
    storage_node = vtkMRMLModelStorageNode()
    storage_node.SetFileName(file_path)
    model_node: vtkMRMLModelNode = a_slicer_app.scene.AddNewNodeByClass(
        "vtkMRMLModelNode"
    )
    storage_node.ReadData(model_node)
    model_node.CreateDefaultDisplayNodes()
    return model_node


@pytest.fixture
def a_segmentation_model(a_slicer_app, a_data_folder):
    return load_model_node(
        a_data_folder.joinpath("segmentation.stl").as_posix(),
        a_slicer_app,
    )


@pytest.fixture
def a_volume_node(a_slicer_app, a_data_folder, a_nrrd_volume_file_path):
    storage_node = vtkMRMLVolumeArchetypeStorageNode()
    node = a_slicer_app.scene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    storage_node.SetFileName(
        a_nrrd_volume_file_path.as_posix(),
    )
    storage_node.ReadData(node)
    node.SetAndObserveStorageNodeID(storage_node.GetID())

    return node


def pytest_addoption(parser):
    parser.addoption("--render_interactive", action="store", default=0)


@pytest.fixture(scope="session")
def render_interactive(pytestconfig):
    return float(pytestconfig.getoption("render_interactive"))


@pytest.fixture()
def a_server(render_interactive):
    server = get_server(None, client_type="vue3")

    async def stop_server(stop_time_s):
        await server.ready
        await asyncio.sleep(stop_time_s)
        await server.stop()

    _server_start = server.start

    def limited_time_start(*args, **kwargs):
        interactive_time_s = max(0.1, render_interactive)
        create_task(stop_server(stop_time_s=interactive_time_s))

        # If render interactive time is very small, opening browser may make the tests hang.
        # For rendering time less than 1 second, disable browser opening.
        open_browser = bool(render_interactive > 1)
        _server_start(open_browser=open_browser, *args, **kwargs)

    server.start = limited_time_start

    try:
        yield server
    finally:
        server.start = _server_start
