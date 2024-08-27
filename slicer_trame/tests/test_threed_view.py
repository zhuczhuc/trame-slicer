def test_threed_view_can_render_mrml_models(
    a_threed_view, a_model_node, render_interactive
):
    a_threed_view.reset_camera()
    a_threed_view.reset_focal_point()
    a_threed_view.render()

    if render_interactive:
        a_threed_view.interactor().Start()


def test_threed_view_can_render_mrml_volumes(
    a_threed_view,
    a_slice_view,
    a_volume_node,
    a_slicer_app,
    render_interactive,
):
    # Use slice view to avoid warnings in test
    a_slice_view.set_background_volume_id(a_volume_node.GetID())
    a_slicer_app.volume_rendering.create_display_node(a_volume_node, "MR-Default")
    a_volume_node.GetDisplayNode().SetVisibility(True)
    a_threed_view.reset_camera()
    a_threed_view.reset_focal_point()
    a_threed_view.render()

    if render_interactive:
        a_threed_view.interactor().Start()
