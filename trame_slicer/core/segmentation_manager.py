from typing import Optional

from slicer import (
    vtkMRMLLabelMapVolumeNode,
    vtkMRMLModelNode,
    vtkMRMLScalarVolumeNode,
    vtkMRMLScene,
    vtkMRMLSegmentationNode,
    vtkSlicerSegmentationsModuleLogic,
)

from trame_slicer.segmentation import Segmentation, SegmentationEditor

from .view_manager import ViewManager


class SegmentationManager:
    """
    Helper class to load and display segmentations in given view group
    """

    def __init__(
        self,
        logic: vtkSlicerSegmentationsModuleLogic,
        view_manager: ViewManager,
        scene: vtkMRMLScene,
    ) -> None:
        self._logic = logic
        self._view_manager = view_manager
        self._scene = scene
        self._segmentations: list[Segmentation] = []

    @property
    def segmentations(self) -> list[Segmentation]:
        return self._segmentations

    def create_segmentation(
        self,
        segmentation_node: vtkMRMLSegmentationNode,
        volume: vtkMRMLScalarVolumeNode,
        view_group: Optional[int] = None,
    ) -> Segmentation:
        # Display segmentation by default
        segmentation_node.SetDisplayVisibility(True)
        segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(volume)
        segmentation_node.GetSegmentation().SetConversionParameter(
            "Conversion method", "1"
        )
        segmentation_node.GetSegmentation().SetConversionParameter(
            "SurfaceNets smoothing", "1"
        )

        editor = SegmentationEditor(segmentation_node, volume)
        editor.sanitize_segmentation()

        segmentation = Segmentation(editor, self._view_manager.get_views(view_group))

        self._segmentations.append(segmentation)
        return self._segmentations[-1]

    def delete_segmentation(self, segmentation: Segmentation) -> None:
        self._segmentations.remove(segmentation)

    def load_segmentation_model(
        self, model: vtkMRMLModelNode, volume: vtkMRMLScalarVolumeNode
    ) -> Segmentation:
        segmentation_node = self._create_segmentation_node(volume)
        self._logic.ImportModelToSegmentationNode(model, segmentation_node, "")
        return self.create_segmentation(segmentation_node, volume)

    def load_segmentation_labelmap(
        self, labelmap: vtkMRMLLabelMapVolumeNode, volume: vtkMRMLScalarVolumeNode
    ) -> Segmentation:
        segmentation_node = self._create_segmentation_node(volume)
        self._logic.ImportLabelmapToSegmentationNode(labelmap, segmentation_node, "")
        return self.create_segmentation(segmentation_node, volume)

    def _create_segmentation_node(
        self, volume: vtkMRMLScalarVolumeNode
    ) -> vtkMRMLSegmentationNode:
        segmentation_node: vtkMRMLSegmentationNode = self._scene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode"
        )
        segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(volume)
        return segmentation_node
