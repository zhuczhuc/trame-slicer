def test_threed_view_can_render_mrml_models(a_threed_view, a_model_node):
    a_threed_view.render()


def test_threed_view_can_render_mrml_volumes(a_threed_view, a_volume_node):
    raise NotImplementedError("Missing VolumeRenderingLogic to implement")
