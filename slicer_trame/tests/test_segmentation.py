from vtkmodules.vtkMRMLCore import vtkMRMLSegmentationNode
from vtkmodules.vtkSlicerSegmentationsModuleLogic import vtkSlicerSegmentationsModuleLogic
from vtkmodules.vtkSlicerSegmentationsModuleMRML import vtkMRMLSegmentEditorNode


def test_a_volume_is_compatible_with_segmentation(a_volume_node, a_segmentation_model, a_slicer_app, a_slice_view):
    segmentation_logic = vtkSlicerSegmentationsModuleLogic()
    segmentation_logic.SetMRMLApplicationLogic(a_slicer_app.app_logic)
    segmentation_logic.SetMRMLScene(a_slicer_app.scene)

    segment_editor_node: vtkMRMLSegmentEditorNode = a_slicer_app.scene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    segment_editor_node.SetAndObserveSourceVolumeNode(a_volume_node)

    # Create a segmentation node
    segmentation_node: vtkMRMLSegmentationNode = a_slicer_app.scene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(a_volume_node)
    segment_editor_node.SetAndObserveSegmentationNode(segmentation_node)

    # Push model to segmentation
    segmentation_logic.ImportModelToSegmentationNode(a_segmentation_model, segmentation_node, "")

    # Display segmentation in 3D view
    a_segmentation_model.SetDisplayVisibility(False)
    segmentation_node.SetDisplayVisibility(True)

    a_slice_view.logic.GetSliceCompositeNode().SetBackgroundVolumeID(a_volume_node.GetID())
    a_slice_view.logic.FitSliceToAll()
    a_slice_view.render()
    a_slice_view.interactor().Start()
