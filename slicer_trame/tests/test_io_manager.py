from itertools import chain

import pytest
from vtkmodules.vtkMRMLCore import (
    vtkMRMLModelNode,
    vtkMRMLSegmentationNode,
    vtkMRMLVolumeNode,
)
from vtkmodules.vtkSegmentationCore import vtkSegmentation

from slicer_trame.slicer.io_manager import IOManager
from slicer_trame.slicer.volumes_reader import VolumesReader


@pytest.fixture()
def an_io_manager(a_slicer_app):
    return IOManager(a_slicer_app.scene, a_slicer_app.app_logic)


def test_an_io_manager_can_load_a_volume_using_nifti_format(
    an_io_manager,
    a_slicer_app,
    a_nifti_volume_file_path,
):
    volumes = an_io_manager.load_volumes(a_nifti_volume_file_path.as_posix())
    assert volumes
    assert a_slicer_app.scene.GetNodeByID(volumes[0].GetID()) is not None


def test_an_io_manager_can_load_a_volume_using_nrrd_format(
    an_io_manager,
    a_slicer_app,
    a_nrrd_volume_file_path,
):
    volumes = an_io_manager.load_volumes(a_nrrd_volume_file_path.as_posix())
    assert volumes
    assert a_slicer_app.scene.GetNodeByID(volumes[0].GetID()) is not None


def test_an_io_manager_can_load_a_volume_in_dcm_format(
    an_io_manager,
    a_slicer_app,
    mr_head_dcm_volume_file_paths,
):
    volumes = an_io_manager.load_volumes(
        [p.as_posix() for p in mr_head_dcm_volume_file_paths]
    )
    assert volumes
    assert isinstance(volumes[0], vtkMRMLVolumeNode)
    assert a_slicer_app.scene.GetNodeByID(volumes[0].GetID()) is not None


def test_can_split_multiple_dcm_volumes(
    ct_chest_dcm_volume_file_paths,
    mr_head_dcm_volume_file_paths,
):
    volume_files = [
        p.as_posix()
        for p in chain(mr_head_dcm_volume_file_paths, ct_chest_dcm_volume_file_paths)
    ]
    split_volumes = VolumesReader.split_volumes(volume_files)
    assert len(split_volumes) == 2


def test_split_volume_returns_original_volume_if_nothing_to_split(
    ct_chest_dcm_volume_file_paths,
):
    volume_files = [p.as_posix() for p in ct_chest_dcm_volume_file_paths]
    split_volumes = VolumesReader.split_volumes(volume_files)
    assert len(split_volumes) == 1
    assert split_volumes == [volume_files]


def test_can_load_multiple_volumes_in_dcm_format(
    an_io_manager,
    ct_chest_dcm_volume_file_paths,
    mr_head_dcm_volume_file_paths,
):
    volume_files = [
        p.as_posix()
        for p in chain(mr_head_dcm_volume_file_paths, ct_chest_dcm_volume_file_paths)
    ]

    volumes = an_io_manager.load_volumes(volume_files)
    assert len(volumes) == 2
    assert volumes[0].GetID() != volumes[1].GetID()


def test_an_io_manager_can_load_model_in_stl_format(
    an_io_manager,
    a_model_file_path,
    a_slicer_app,
):
    model = an_io_manager.load_model(a_model_file_path.as_posix())
    assert isinstance(model, vtkMRMLModelNode)
    assert a_slicer_app.scene.GetNodeByID(model.GetID()) is not None


def test_an_io_manager_can_load_segmentations_in_nifti_format(
    an_io_manager,
    a_segmentation_nifti_file_path,
    a_slicer_app,
):
    segmentation_node = an_io_manager.load_segmentation(
        a_segmentation_nifti_file_path.as_posix()
    )
    assert isinstance(segmentation_node, vtkMRMLSegmentationNode)
    assert a_slicer_app.scene.GetNodeByID(segmentation_node.GetID()) is not None
    segmentation: vtkSegmentation = segmentation_node.GetSegmentation()
    assert segmentation.GetNumberOfSegments() == 1


def test_an_io_manager_can_load_segmentations_in_stl_format(
    an_io_manager,
    a_segmentation_stl_file_path,
    a_slicer_app,
):
    segmentation_node = an_io_manager.load_segmentation(
        a_segmentation_stl_file_path.as_posix()
    )
    assert isinstance(segmentation_node, vtkMRMLSegmentationNode)
    assert a_slicer_app.scene.GetNodeByID(segmentation_node.GetID()) is not None
    segmentation: vtkSegmentation = segmentation_node.GetSegmentation()
    assert segmentation.GetNumberOfSegments() == 1
