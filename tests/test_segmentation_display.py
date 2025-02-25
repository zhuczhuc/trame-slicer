from tests.view_events import ViewEvents


def test_segmentation_opacity_can_be_toggled_by_keypress(
    a_slice_view,
    a_segmentation_editor,
    a_volume_node,
    a_segmentation_model,
    render_interactive,
):
    a_slice_view.set_background_volume_id(a_volume_node.GetID())
    node = a_segmentation_editor.create_segmentation_node_from_model_node(
        a_segmentation_model
    )
    a_segmentation_editor.set_active_segmentation(node, a_volume_node)

    ViewEvents(a_slice_view).key_press("g")
    assert node.GetDisplayNode().GetOpacity() == 0.0

    ViewEvents(a_slice_view).key_press("g")
    assert node.GetDisplayNode().GetOpacity() == 1.0

    if render_interactive:
        a_slice_view.interactor().Start()
