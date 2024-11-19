from vtkmodules.vtkMRMLCore import vtkMRMLSegmentationNode
from vtkmodules.vtkSegmentationCore import vtkSegmentation
from vtkmodules.vtkSlicerSegmentationsModuleLogic import (
    vtkSlicerSegmentationsModuleLogic,
)

from trame_slicer.segmentation import (
    BrushModel,
    BrushShape,
    LabelMapOverwriteMode,
    SegmentationEditor,
    SegmentPaintEffect2D,
    SegmentPaintEffect2DInteractor,
    SegmentScissorEffect3D,
    SegmentScissorEffect3DInteractor,
)


def test_segmentation_editor_on_slice(
    a_volume_node,
    a_segmentation_model,
    a_slicer_app,
    a_slice_view,
    render_interactive,
):
    segmentation_logic = vtkSlicerSegmentationsModuleLogic()
    segmentation_logic.SetMRMLApplicationLogic(a_slicer_app.app_logic)
    segmentation_logic.SetMRMLScene(a_slicer_app.scene)

    # Create a segmentation node
    segmentation_node: vtkMRMLSegmentationNode = a_slicer_app.scene.AddNewNodeByClass(
        "vtkMRMLSegmentationNode"
    )
    segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(a_volume_node)

    # Push model to segmentation
    segmentation_logic.ImportModelToSegmentationNode(
        a_segmentation_model, segmentation_node, ""
    )

    segmentation: vtkSegmentation = segmentation_node.GetSegmentation()

    # Display segmentation in 3D view
    a_segmentation_model.SetDisplayVisibility(False)
    segmentation_node.SetDisplayVisibility(True)

    a_slice_view.set_orientation("Sagittal")
    a_slice_view.set_background_volume_id(a_volume_node.GetID())
    a_slice_view.fit_view_to_content()
    a_slice_view.render()
    brush = BrushModel(BrushShape.Cylinder)
    editor = SegmentationEditor(segmentation_node, a_volume_node)
    editor.sanize_segmentation()
    effect = SegmentPaintEffect2D(a_slice_view, editor, brush)
    segmentation.SetConversionParameter("Conversion method", "1")
    segmentation.SetConversionParameter("SurfaceNets smoothing", "1")
    editor.active_segment = segmentation.AddEmptySegment("a", "a", [1.0, 0.0, 0.0])
    editor.overwrite_mode = LabelMapOverwriteMode.Never
    interactor = SegmentPaintEffect2DInteractor(effect)
    a_slice_view.add_user_interactor(interactor)

    if render_interactive:
        a_slice_view.interactor().Start()


def test_segmentation_editor_on_volume(
    a_volume_node,
    a_segmentation_model,
    a_slicer_app,
    a_threed_view,
    render_interactive,
):
    # Create a segmentation node
    segmentation_node: vtkMRMLSegmentationNode = a_slicer_app.scene.AddNewNodeByClass(
        "vtkMRMLSegmentationNode"
    )
    segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(a_volume_node)

    # Push model to segmentation
    a_slicer_app.segmentation_logic.ImportModelToSegmentationNode(
        a_segmentation_model, segmentation_node, ""
    )

    segmentation_node.GetSegmentation()

    # Display segmentation in 3D view
    a_segmentation_model.SetDisplayVisibility(False)
    segmentation_node.SetDisplayVisibility(True)

    a_slicer_app.volume_rendering.create_display_node(a_volume_node, "MR-Default")
    a_volume_node.GetDisplayNode().SetVisibility(True)
    a_threed_view.reset_camera()
    a_threed_view.reset_focal_point()
    a_threed_view.render()

    editor = SegmentationEditor(segmentation_node, a_volume_node)
    editor.sanize_segmentation()
    editor.enable_surface_representation()

    # scissor_brush = ScissorPolygonBrush(a_threed_view.render_window())
    # scissor_brush.widget.On()

    scissor = SegmentScissorEffect3D(a_threed_view, editor)
    scissor.enable_brush()
    interactor = SegmentScissorEffect3DInteractor(scissor)
    a_threed_view.add_user_interactor(interactor)

    # brush_model = BrushModel(BrushShape.Sphere)
    # effect3D = SegmentPaintEffect3D(a_threed_view, editor, brush_model)
    # segmentation.SetConversionParameter("Conversion method", "1")
    # segmentation.SetConversionParameter("SurfaceNets smoothing", "1")
    # interactor = SegmentPaintEffect3DInteractor(effect3D)
    # a_threed_view.add_user_interactor(interactor)

    # if render_interactive:
    a_threed_view.render_window().ShowWindowOn()
    a_threed_view.interactor().Start()
