from pathlib import Path
from typing import Optional, Union

from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkMRMLCore import (
    vtkMRMLModelNode,
    vtkMRMLModelStorageNode,
    vtkMRMLScene,
    vtkMRMLSegmentationNode,
    vtkMRMLVolumeNode,
)
from vtkmodules.vtkMRMLLogic import vtkMRMLApplicationLogic
from vtkmodules.vtkSegmentationCore import vtkSegment, vtkSegmentationConverter
from vtkmodules.vtkSlicerSegmentationsModuleLogic import (
    vtkSlicerSegmentationsModuleLogic,
)

from .volumes_reader import VolumesReader


class IOManager:
    """
    Class responsible for loading files in the scene.
    """

    def __init__(self, scene: vtkMRMLScene, app_logic: vtkMRMLApplicationLogic):
        self.scene = scene
        self.app_logic = app_logic

    def load_volumes(
        self,
        volume_files: Union[str, list[str]],
    ) -> list[vtkMRMLVolumeNode]:
        return VolumesReader.load_volumes(self.scene, self.app_logic, volume_files)

    def load_model(self, model_file: str) -> Optional[vtkMRMLModelNode]:
        model_file = Path(model_file).resolve()
        if not model_file.is_file():
            return None

        storage_node = vtkMRMLModelStorageNode()
        storage_node.SetFileName(model_file.as_posix())
        model_name = model_file.stem
        model_node: vtkMRMLModelNode = self.scene.AddNewNodeByClass(
            "vtkMRMLModelNode", model_name
        )
        storage_node.ReadData(model_node)
        model_node.CreateDefaultDisplayNodes()
        return model_node

    def load_segmentation(
        self,
        segmentation_file: str,
    ) -> Optional[vtkMRMLSegmentationNode]:
        """
        Adapted from Modules/Loadable/Segmentations/qSlicerSegmentationsReader.cxx
        """
        segmentation_file = Path(segmentation_file).resolve()
        if not segmentation_file.is_file():
            return None

        node_name = segmentation_file.stem
        if segmentation_file.suffix in [".obj", ".stl"]:
            return self._load_segmentation_from_model_file(segmentation_file, node_name)

        logic = vtkSlicerSegmentationsModuleLogic()
        logic.SetMRMLApplicationLogic(self.app_logic)
        logic.SetMRMLScene(self.scene)
        return logic.LoadSegmentationFromFile(
            segmentation_file.as_posix(), True, node_name
        )

    def _load_segmentation_from_model_file(
        self,
        segmentation_file: Path,
        node_name: str,
    ) -> Optional[vtkMRMLSegmentationNode]:
        """
        Adapted from Modules/Loadable/Segmentations/qSlicerSegmentationsReader.cxx
        """
        model_storage_node = vtkMRMLModelStorageNode()
        model_storage_node.SetFileName(segmentation_file.as_posix())
        model_node = vtkMRMLModelNode()
        if not model_storage_node.ReadData(model_node):
            return None

        closed_surface_representation: vtkPolyData = model_node.GetPolyData()
        if not closed_surface_representation:
            return None

        point_data = closed_surface_representation.GetPointData()
        if not point_data:
            return None

        while point_data.GetNumberOfArrays() > 0:
            point_data.RemoveArray(0)

        segment = vtkSegment()
        segment.SetName(node_name)
        closed_surface_tag = (
            vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName()
        )
        segment.AddRepresentation(
            closed_surface_tag,
            closed_surface_representation,
        )

        segmentation_node: vtkMRMLSegmentationNode = self.scene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode",
            node_name,
        )
        segmentation_node.SetSourceRepresentationToClosedSurface()
        segmentation_node.CreateDefaultDisplayNodes()
        segmentation_node.GetSegmentation().AddSegment(segment)

        display_node = segmentation_node.GetDisplayNode()
        if display_node:
            display_node.SetPreferredDisplayRepresentationName2D(closed_surface_tag)

        return segmentation_node
