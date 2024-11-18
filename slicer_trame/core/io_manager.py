from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, Union
from zipfile import ZipFile

from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkMRMLCore import (
    vtkMRMLModelNode,
    vtkMRMLModelStorageNode,
    vtkMRMLScene,
    vtkMRMLSegmentationNode,
    vtkMRMLSegmentationStorageNode,
    vtkMRMLStorageNode,
    vtkMRMLVolumeNode,
)
from vtkmodules.vtkMRMLLogic import vtkMRMLApplicationLogic, vtkMRMLRemoteIOLogic
from vtkmodules.vtkSegmentationCore import vtkSegment, vtkSegmentationConverter
from vtkmodules.vtkSlicerBaseLogic import vtkDataIOManagerLogic
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

        # Configure IO logic to enable loading from MRB format
        self.cache_dir = TemporaryDirectory()

        self.remote_io = vtkMRMLRemoteIOLogic()
        self.remote_io.SetMRMLScene(self.scene)
        self.remote_io.SetMRMLApplicationLogic(self.app_logic)
        self.remote_io.GetCacheManager().SetRemoteCacheDirectory(self.cache_dir.name)

        self.vtk_io_manager_logic = vtkDataIOManagerLogic()
        self.vtk_io_manager_logic.SetMRMLScene(scene)
        self.vtk_io_manager_logic.SetMRMLApplicationLogic(app_logic)
        self.vtk_io_manager_logic.SetAndObserveDataIOManager(
            self.remote_io.GetDataIOManager()
        )
        self.remote_io.AddDataIOToScene()

    def load_volumes(
        self,
        volume_files: Union[str, list[str]],
    ) -> list[vtkMRMLVolumeNode]:
        return VolumesReader.load_volumes(self.scene, self.app_logic, volume_files)

    def load_model(
        self,
        model_file: Union[str, Path],
        do_convert_to_slicer_coord: bool = True,
    ) -> Optional[vtkMRMLModelNode]:
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

        # Check if RAS / LPS conversion is required
        # Slicer will read coordinates in the file header during load regarding of preferred load format
        # Check if coordinate change occurred to rollback change if requested
        did_convert_coord = (
            storage_node.GetCoordinateSystem() != vtkMRMLStorageNode.CoordinateSystemRAS
        )
        if not do_convert_to_slicer_coord and did_convert_coord:
            storage_node.ConvertBetweenRASAndLPS(
                model_node.GetPolyData(), model_node.GetPolyData()
            )

        model_node.CreateDefaultDisplayNodes()
        return model_node

    @classmethod
    def write_model(
        cls,
        model_node,
        model_file: Union[str, Path],
        do_convert_from_slicer_coord: bool = True,
    ) -> None:
        cls._write_node(
            model_node,
            model_file,
            vtkMRMLModelStorageNode,
            do_convert_from_slicer_coord,
        )

    def load_segmentation(
        self,
        segmentation_file: Union[str, Path],
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

    @classmethod
    def write_segmentation(
        cls,
        segmentation_node,
        segmentation_file: Union[str, Path],
        do_convert_from_slicer_coord: bool = True,
    ):
        cls._write_node(
            segmentation_node,
            segmentation_file,
            vtkMRMLSegmentationStorageNode,
            do_convert_from_slicer_coord,
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

    @classmethod
    def _write_node(
        cls,
        node,
        node_file,
        storage_type: type,
        do_convert_from_slicer_coord: bool,
    ) -> None:
        if not node:
            return

        node_file = Path(node_file).resolve().as_posix()
        storage_node = storage_type()

        if hasattr(storage_node, "SetCoordinateSystem"):
            storage_node.SetCoordinateSystem(
                vtkMRMLStorageNode.CoordinateSystemLPS
                if do_convert_from_slicer_coord
                else vtkMRMLStorageNode.CoordinateSystemRAS
            )
        storage_node.SetFileName(node_file)
        storage_node.WriteData(node)

    def load_scene(self, scene_path) -> bool:
        scene_path = Path(scene_path)
        if not scene_path.is_file():
            return False

        if scene_path.name.endswith("mrb"):
            return self._load_mrb_scene(scene_path)
        return self._load_mrml_scene(scene_path)

    def _load_mrml_scene(self, scene_path: Path) -> bool:
        if not scene_path.is_file():
            return False
        self.scene.SetURL(scene_path.as_posix())
        return self.scene.Import(None)

    def _load_mrb_scene(self, scene_path: Path) -> bool:
        try:
            with TemporaryDirectory() as tmpdir:
                with ZipFile(scene_path, "r") as zip_file:
                    zip_file.extractall(tmpdir)
                    return self._load_mrml_scene(next(Path(tmpdir).rglob("*.mrml")))
        except StopIteration:
            return False
