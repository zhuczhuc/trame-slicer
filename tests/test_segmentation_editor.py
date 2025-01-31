import numpy as np
import pytest
from slicer import (
    vtkMRMLSegmentationDisplayNode,
    vtkMRMLSegmentationNode,
    vtkSegmentation,
    vtkSegmentationConverter,
    vtkSlicerSegmentationsModuleLogic,
)
from vtkmodules.vtkCommonCore import VTK_UNSIGNED_CHAR
from vtkmodules.vtkCommonDataModel import vtkImageData

from trame_slicer.segmentation import (
    LabelMapOverwriteMode,
    SegmentationEditor,
    vtk_image_to_np,
)


@pytest.fixture
def a_simple_segmentation(a_slicer_app, a_data_folder):
    return a_slicer_app.io_manager.load_model(
        a_data_folder.joinpath("simple_segmentation.stl").as_posix()
    )


@pytest.fixture
def a_simple_volume(a_slicer_app, a_data_folder, a_nrrd_volume_file_path):
    return a_slicer_app.io_manager.load_volumes(
        a_data_folder.joinpath("simple_volume.nii").as_posix()
    )[-1]


def check_labelmap_is(labelmap: np.ndarray, expected) -> None:
    assert np.array_equal(labelmap, np.array(expected, np.uint8))


def test_segmentation_editor(a_simple_volume, a_simple_segmentation, a_slicer_app):
    segmentation_logic = vtkSlicerSegmentationsModuleLogic()
    segmentation_logic.SetMRMLApplicationLogic(a_slicer_app.app_logic)
    segmentation_logic.SetMRMLScene(a_slicer_app.scene)

    # Create a segmentation node
    segmentation_node: vtkMRMLSegmentationNode = a_slicer_app.scene.AddNewNodeByClass(
        "vtkMRMLSegmentationNode"
    )
    segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(a_simple_volume)

    # Push model to segmentation
    segmentation_logic.ImportModelToSegmentationNode(
        a_simple_segmentation, segmentation_node, ""
    )
    segmentation: vtkSegmentation = segmentation_node.GetSegmentation()

    display_node = vtkMRMLSegmentationDisplayNode.SafeDownCast(
        segmentation_node.GetDisplayNode()
    )

    vtk_labelmap = vtkImageData.SafeDownCast(
        segmentation.GetNthSegment(0).GetRepresentation(
            vtkSegmentationConverter.GetBinaryLabelmapRepresentationName()
        )
    )

    editor = SegmentationEditor(segmentation_node, a_simple_volume)
    editor.sanitize_segmentation()
    editor.active_segment = segmentation.GetNthSegmentID(0)

    labelmap = vtk_image_to_np(vtk_labelmap)
    check_labelmap_is(labelmap, [[[1, 0], [0, 0]], [[0, 0], [0, 0]]])

    vtk_modifier = vtkImageData()
    vtk_modifier.SetExtent(list(vtk_labelmap.GetExtent()))
    vtk_modifier.AllocateScalars(VTK_UNSIGNED_CHAR, 1)  # booleans
    vtk_modifier.GetPointData().GetScalars().Fill(0)
    modifier = vtk_image_to_np(vtk_modifier)
    modifier[1, 0, 0] = 1

    editor.apply_labelmap(vtk_modifier)
    check_labelmap_is(labelmap, [[[1, 0], [0, 0]], [[1, 0], [0, 0]]])

    editor.active_segment = segmentation.AddEmptySegment("2", "2", [1.0, 0.0, 0.0])
    editor.apply_labelmap(vtk_modifier)
    check_labelmap_is(labelmap, [[[1, 0], [0, 0]], [[2, 0], [0, 0]]])

    editor.overwrite_mode = LabelMapOverwriteMode.Never
    editor.active_segment = segmentation.GetNthSegmentID(0)
    editor.apply_labelmap(vtk_modifier)
    check_labelmap_is(labelmap, [[[1, 0], [0, 0]], [[2, 0], [0, 0]]])  # no change

    modifier[1, 0, 1] = 1
    editor.apply_labelmap(vtk_modifier)
    check_labelmap_is(
        labelmap, [[[1, 0], [0, 0]], [[2, 1], [0, 0]]]
    )  # only 0 will change

    modifier[1, 1, 0] = 1
    modifier[1, 1, 1] = 1
    display_node.SetSegmentVisibility(
        segmentation.GetNthSegmentID(1), False
    )  # hide segment 1
    editor.overwrite_mode = LabelMapOverwriteMode.VisibleSegments
    editor.active_segment = segmentation.AddEmptySegment("3", "3", [0.0, 1.0, 0.0])
    editor.apply_labelmap(vtk_modifier)
    check_labelmap_is(
        labelmap, [[[1, 0], [0, 0]], [[2, 3], [0, 0]]]
    )  # only 1 will change


def test_segmentation_editor_with_mask(
    a_simple_volume, a_simple_segmentation, a_slicer_app
):
    segmentation_logic = vtkSlicerSegmentationsModuleLogic()
    segmentation_logic.SetMRMLApplicationLogic(a_slicer_app.app_logic)
    segmentation_logic.SetMRMLScene(a_slicer_app.scene)

    # Create a segmentation node
    segmentation_node: vtkMRMLSegmentationNode = a_slicer_app.scene.AddNewNodeByClass(
        "vtkMRMLSegmentationNode"
    )
    segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(a_simple_volume)

    # Push model to segmentation
    segmentation_logic.ImportModelToSegmentationNode(
        a_simple_segmentation, segmentation_node, ""
    )
    segmentation: vtkSegmentation = segmentation_node.GetSegmentation()

    display_node = vtkMRMLSegmentationDisplayNode.SafeDownCast(
        segmentation_node.GetDisplayNode()
    )

    vtk_labelmap = vtkImageData.SafeDownCast(
        segmentation.GetNthSegment(0).GetRepresentation(
            vtkSegmentationConverter.GetBinaryLabelmapRepresentationName()
        )
    )

    editor = SegmentationEditor(segmentation_node, a_simple_volume)
    editor.mask = np.array(
        [[[True, False], [True, False]], [[True, False], [False, False]]], dtype=np.bool
    )

    labelmap = vtk_image_to_np(vtk_labelmap)
    check_labelmap_is(labelmap, [[[1, 0], [0, 0]], [[0, 0], [0, 0]]])

    vtk_modifier = vtkImageData()
    vtk_modifier.SetExtent(list(vtk_labelmap.GetExtent()))
    vtk_modifier.AllocateScalars(VTK_UNSIGNED_CHAR, 1)  # booleans
    vtk_modifier.GetPointData().GetScalars().Fill(0)
    modifier = vtk_image_to_np(vtk_modifier)
    modifier[1, 0, 0] = 1
    modifier[1, 0, 1] = 1  # out of mask!

    editor.apply_labelmap(vtk_modifier)
    check_labelmap_is(labelmap, [[[1, 0], [0, 0]], [[1, 0], [0, 0]]])

    editor.active_segment = segmentation.AddEmptySegment("2", "2", [1.0, 0.0, 0.0])
    editor.apply_labelmap(vtk_modifier)
    check_labelmap_is(labelmap, [[[1, 0], [0, 0]], [[2, 0], [0, 0]]])

    editor.overwrite_mode = LabelMapOverwriteMode.Never
    editor.active_segment = segmentation.GetNthSegmentID(0)
    editor.apply_labelmap(vtk_modifier)
    check_labelmap_is(labelmap, [[[1, 0], [0, 0]], [[2, 0], [0, 0]]])  # no change

    modifier[1, 0, 1] = 1
    editor.apply_labelmap(vtk_modifier)
    check_labelmap_is(labelmap, [[[1, 0], [0, 0]], [[2, 0], [0, 0]]])  # no change
    editor.mask[1, 0, 1] = True
    editor.apply_labelmap(vtk_modifier)
    check_labelmap_is(
        labelmap, [[[1, 0], [0, 0]], [[2, 1], [0, 0]]]
    )  # only 0 will change

    editor.mask[1, 0, 1] = False
    editor.mask[1, 1, 0] = True
    editor.mask[1, 1, 1] = True
    modifier[1, 1, 0] = 1
    modifier[1, 1, 1] = 1
    display_node.SetSegmentVisibility(
        segmentation.GetNthSegmentID(1), False
    )  # hide segment 1
    editor.overwrite_mode = LabelMapOverwriteMode.VisibleSegments
    editor.active_segment = segmentation.AddEmptySegment("3", "3", [0.0, 1.0, 0.0])
    editor.apply_labelmap(vtk_modifier)
    check_labelmap_is(labelmap, [[[1, 0], [0, 0]], [[2, 1], [0, 0]]])  # no change

    editor.mask[1, 0, 1] = True
    editor.apply_labelmap(vtk_modifier)
    check_labelmap_is(
        labelmap, [[[1, 0], [0, 0]], [[2, 3], [0, 0]]]
    )  # only 1 will change
