from vtkmodules.vtkMRMLCore import vtkMRMLScalarVolumeDisplayNode, vtkMRMLSliceNode
from vtkmodules.vtkMRMLLogic import vtkMRMLSliceLogic

def test_slice_view_can_display_volume(a_slice_view, a_volume_node, a_slicer_app):
    a_slice_view.logic.GetSliceCompositeNode().SetBackgroundVolumeID(a_volume_node.GetID())

    a_slice_view.first_renderer().SetBackground(1.0, .0, .0)
    a_slice_view.mrml_view_node.SetOrientation("Coronal")
    a_slice_view.logic.FitSliceToAll()

    display: vtkMRMLScalarVolumeDisplayNode = a_volume_node.GetDisplayNode()
    assert display
    # display.SetAutoWindowLevel(False)
    # display.SetWindow(1)
    # display.Modified()
    # a_slice_view.logic.UpdatePipeline()
    # a_slice_view.render_manager.SetImageDataConnection(display.GetImageDataConnection())

    # display.AutoWindowLevelOn()
    # display.AutoScalarRangeOn()

    # displayRange = [0] * 2
    # display.GetDisplayScalarRange(displayRange)
    # print(displayRange)


    # a0 = list(a_slice_view.first_renderer().GetActors2D())[-1]
    # m0 = a0.GetMapper()

    # vtk
    # m0.GetInputAlgorithm().GetInputAlgorithm().GetInputAlgorithm().GetInputAlgorithm().SetOutputFormatToRGB()

    a_slice_view.render()
    a_slice_view.first_renderer().ResetCamera()

    a_slice_view.render()
    a_slice_view.interactor().Start()
