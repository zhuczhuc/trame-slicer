import asyncio

import itk
import pytest
from trame.app import get_server
from trame_server.utils.asynchronous import create_task
from vtkmodules.vtkMRMLCore import (
    vtkMRMLColorTableNode,
    vtkMRMLModelNode,
    vtkMRMLModelStorageNode,
    vtkMRMLScalarVolumeDisplayNode,
    vtkMRMLScalarVolumeNode,
    vtkMRMLVolumeArchetypeStorageNode,
)

from slicer_trame.slicer.render_scheduler import DirectRendering
from slicer_trame.slicer.slice_view import SliceView
from slicer_trame.slicer.slicer_app import SlicerApp
from slicer_trame.slicer.threed_view import ThreeDView


@pytest.fixture
def a_slicer_app():
    return SlicerApp()


@pytest.fixture
def a_threed_view(a_slicer_app):
    three_d_view = ThreeDView(
        a_slicer_app.scene,
        a_slicer_app.app_logic,
        "ThreeD",
        scheduled_render_strategy=DirectRendering(),
    )
    yield three_d_view
    three_d_view.finalize()


@pytest.fixture
def a_slice_view(a_slicer_app):
    return SliceView(
        a_slicer_app.scene,
        a_slicer_app.app_logic,
        "Red",
        scheduled_render_strategy=DirectRendering(),
    )


@pytest.fixture
def a_model_node(a_slicer_app):
    return load_model_node(
        r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\test_data\model.stl",
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
def a_segmentation_model(a_slicer_app):
    return load_model_node(
        r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\test_data\a_segmentation.stl",
        a_slicer_app,
    )


@pytest.fixture
def a_volume_node(a_slicer_app):
    storage_node = vtkMRMLVolumeArchetypeStorageNode()
    node = a_slicer_app.scene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    storage_node.SetFileName(
        r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\test_data\MRHead.nrrd"
    )
    storage_node.ReadData(node)
    node.SetAndObserveStorageNodeID(storage_node.GetID())

    return node


@pytest.fixture
def a_volume_node_manually_loaded(a_slicer_app):
    im = itk.imread(
        r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\test_data\MRHead.nrrd"
    )
    vtk_image = itk.vtk_image_from_image(im)
    node: vtkMRMLScalarVolumeNode = a_slicer_app.scene.AddNewNodeByClass(
        "vtkMRMLScalarVolumeNode"
    )
    node.SetAndObserveImageData(vtk_image)
    node.CreateDefaultDisplayNodes()
    return node


@pytest.fixture
def a_volume_manually_crafted(a_slicer_app):
    import vtk

    displayNode = vtkMRMLScalarVolumeDisplayNode()
    scalarNode = vtkMRMLScalarVolumeNode()

    displayNode.SetAutoWindowLevel(True)
    displayNode.SetInterpolate(False)

    scalarNode.SetName("foo")
    scalarNode.SetScene(a_slicer_app.scene)
    displayNode.SetScene(a_slicer_app.scene)

    imageData = vtk.vtkImageData()
    imageData.SetDimensions(10, 20, 30)
    imageData.AllocateScalars(vtk.VTK_FLOAT, 1)
    imageData.GetPointData().GetScalars().Fill(12.5)

    a_slicer_app.scene.AddNode(displayNode)
    scalarNode.SetAndObserveDisplayNodeID(displayNode.GetID())
    scalarNode.SetAndObserveImageData(imageData)
    a_slicer_app.scene.AddNode(scalarNode)

    colorNode = vtkMRMLColorTableNode()
    colorNode.SetTypeToGrey()
    a_slicer_app.scene.AddNode(colorNode)

    displayNode.SetAndObserveColorNodeID(colorNode.GetID())

    return scalarNode


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
