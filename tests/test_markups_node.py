from vtkmodules.vtkSlicerMarkupsModuleMRML import vtkMRMLMarkupsFiducialNode


def test_can_load_scene_with_markups(
    a_slicer_app,
    a_threed_view,
    render_interactive,
    a_data_folder,
):
    a_slicer_app.scene.ReadFromMRB(
        a_data_folder.joinpath("markups_scene.mrb").as_posix()
    )

    assert list(a_slicer_app.scene.GetNodesByClass("vtkMRMLMarkupsFiducialNode"))
    assert list(a_slicer_app.scene.GetNodesByClass("vtkMRMLMarkupsLineNode"))
    assert list(a_slicer_app.scene.GetNodesByClass("vtkMRMLMarkupsAngleNode"))
    assert list(a_slicer_app.scene.GetNodesByClass("vtkMRMLMarkupsCurveNode"))

    a_threed_view.reset_view()
    if render_interactive:
        a_threed_view.interactor().Start()


def test_markups_nodes_can_be_placed_interactively(
    a_slicer_app,
    a_threed_view,
    a_model_node,
    render_interactive,
):
    markups_node: vtkMRMLMarkupsFiducialNode = a_slicer_app.scene.AddNewNodeByClass(
        "vtkMRMLMarkupsFiducialNode"
    )
    markups_node.AddControlPointWorld([-60, -40, 44], "F")
    assert markups_node.GetDisplayNode() is not None
    markups_node.SetDisplayVisibility(True)

    a_slicer_app.markups_logic.SetActiveList(markups_node)
    a_slicer_app.markups_logic.StartPlaceMode(True)

    if render_interactive:
        a_threed_view.interactor().Start()
