def test_slice_view_can_display_volume(a_slice_view, a_volume_node, a_slicer_app):
    a_slice_view.logic.GetSliceCompositeNode().SetBackgroundVolumeID(a_volume_node.GetID())

    a_slice_view.first_renderer().SetBackground(1.0, .0, .0)
    a_slice_view.mrml_view_node.SetOrientation("Coronal")

    a_slice_view.logic.FitSliceToAll()
    a_slice_view.interactor().EnableRenderOff()

    a_slice_view.render()
    a_slice_view.interactor().Start()
