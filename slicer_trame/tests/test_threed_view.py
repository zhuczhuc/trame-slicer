from vtkmodules.vtkSlicerVolumeRenderingModuleLogic import vtkSlicerVolumeRenderingLogic


def test_threed_view_can_render_mrml_models(a_threed_view, a_model_node):
    a_threed_view.reset_camera()
    a_threed_view.reset_focal_point()
    a_threed_view.render()
    a_threed_view.interactor().Start()



def test_threed_view_can_render_mrml_volumes(a_threed_view, a_slice_view, a_volume_node, a_slicer_app):
    a_slice_view.logic.GetSliceCompositeNode().SetBackgroundVolumeID(a_volume_node.GetID())
    logic = vtkSlicerVolumeRenderingLogic()
    logic.SetMRMLApplicationLogic(a_slicer_app.app_logic)
    logic.SetMRMLScene(a_slicer_app.scene)
    logic.SetModuleShareDirectory(r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\slicer_trame\resources")
    logic.ChangeVolumeRenderingMethod("vtkMRMLGPURayCastVolumeRenderingDisplayNode")
    display = logic.CreateDefaultVolumeRenderingNodes(a_volume_node)
    a_volume_node.CreateDefaultDisplayNodes()
    a_volume_node.AddAndObserveDisplayNodeID(display.GetID())

    display.GetVolumePropertyNode().Copy(logic.GetPresetByName("MR-Default"))

    a_volume_node.GetDisplayNode().SetVisibility(True)
    display.SetVisibility(True)
    a_threed_view.reset_camera()
    a_threed_view.reset_focal_point()
    a_threed_view.render()
    a_threed_view.interactor().Start()
