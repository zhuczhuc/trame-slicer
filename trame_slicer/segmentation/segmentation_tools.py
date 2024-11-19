from enum import IntEnum

from trame_slicer.segmentation import (
    BrushModel,
    BrushShape,
    LabelMapOperation,
    SegmentationEditor,
    SegmentPaintEffect2D,
    SegmentPaintEffect2DInteractor,
    SegmentPaintEffect3D,
    SegmentPaintEffect3DInteractor,
    SegmentScissorEffect3D,
    SegmentScissorEffect3DInteractor,
)
from trame_slicer.views import AbstractView, SliceView, ThreeDView


class SegmentationToolID(IntEnum):
    NoTool = 0
    PaintErase = 1
    Scissor = 2


class SegmentationTool:
    def __init__(self, editor: SegmentationEditor) -> None:
        self._editor = editor
        self._id = SegmentationToolID.NoTool

    def activate(self, views: list[AbstractView]) -> None:
        pass

    def deactivate(self) -> None:
        pass

    @property
    def erasing(self) -> bool:
        return self._editor.operation == LabelMapOperation.Erase

    @erasing.setter
    def erasing(self, erase: bool):
        self._editor.operation = (
            LabelMapOperation.Erase if erase else LabelMapOperation.Set
        )


class SegmentationPaintEraseTool(SegmentationTool):
    def __init__(self, editor: SegmentationEditor) -> None:
        super().__init__(editor)
        self._brush_model = BrushModel(BrushShape.Sphere)
        self._3d_effects: dict[ThreeDView, SegmentPaintEffect3DInteractor] = {}
        self._2d_effects: dict[SliceView, SegmentPaintEffect2DInteractor] = {}

    @property
    def brush_model(self) -> BrushModel:
        return self._brush_model

    def activate(self, views: list[AbstractView]) -> None:
        for view in [v for v in views if isinstance(v, ThreeDView)]:
            if view not in self._3d_effects:
                effect = SegmentPaintEffect3D(view, self._editor, self._brush_model)
                interactor = SegmentPaintEffect3DInteractor(effect)
                interactor.render_callback = self._render_all_views
                self._3d_effects[view] = interactor

            interactor = self._3d_effects[view]
            interactor.effect.enable_brush()
            view.add_user_interactor(interactor)
            view.reset_camera()
            view.reset_focal_point()
            view.render()

        for view in [v for v in views if isinstance(v, SliceView)]:
            if view not in self._2d_effects:
                effect = SegmentPaintEffect2D(view, self._editor, self._brush_model)
                interactor = SegmentPaintEffect2DInteractor(effect)
                interactor.render_callback = self._render_all_views
                self._2d_effects[view] = interactor

            interactor = self._2d_effects[view]
            interactor.effect.enable_brush()
            view.add_user_interactor(interactor)

    def deactivate(self) -> None:
        for [view, interactor] in self._3d_effects.items():
            interactor.effect.disable_brush()
            view.remove_user_interactor(interactor)

        for [view, interactor] in self._2d_effects.items():
            interactor.effect.disable_brush()
            view.remove_user_interactor(interactor)

    def _render_all_views(self):
        for view in self._3d_effects:
            view.schedule_render()

        for view in self._2d_effects:
            view.schedule_render()


class SegmentationScissorTool(SegmentationTool):
    def __init__(self, editor: SegmentationEditor) -> None:
        super().__init__(editor)
        self._brush_model = BrushModel(BrushShape.Sphere)
        self._3d_effects: dict[ThreeDView, SegmentScissorEffect3DInteractor] = {}
        # self._2d_effects: dict[SliceView, SegmentPaintEffect2DInteractor] = {}

    def activate(self, views: list[AbstractView]) -> None:
        for view in [v for v in views if isinstance(v, ThreeDView)]:
            if view not in self._3d_effects:
                effect = SegmentScissorEffect3D(view, self._editor)
                interactor = SegmentScissorEffect3DInteractor(effect)
                interactor.render_callback = self._render_all_views
                self._3d_effects[view] = interactor

            interactor = self._3d_effects[view]
            interactor.effect.enable_brush()
            view.add_user_interactor(interactor)
            view.schedule_render()

    def deactivate(self) -> None:
        for [view, interactor] in self._3d_effects.items():
            interactor.effect.disable_brush()

    def _render_all_views(self):
        for view in self._3d_effects:
            view.schedule_render()


class Segmentation:
    def __init__(self, editor: SegmentationEditor, views: list[AbstractView]) -> None:
        self._editor = editor
        self._active_tool = SegmentationToolID.NoTool
        self._effects: dict[SegmentationToolID, SegmentationTool] = {
            SegmentationToolID.NoTool: SegmentationTool(editor),
            SegmentationToolID.PaintErase: SegmentationPaintEraseTool(editor),
            SegmentationToolID.Scissor: SegmentationScissorTool(editor),
        }
        self._views = views

    @property
    def active_tool(self) -> SegmentationToolID:
        return self._active_tool

    @active_tool.setter
    def active_tool(self, effect: SegmentationToolID) -> None:
        self._effects[self._active_tool].deactivate()
        self._active_tool = effect
        self._effects[self._active_tool].activate(self._views)

    @property
    def tool(self) -> SegmentationTool:
        return self._effects[self._active_tool]

    def delete(self) -> None:
        self.active_tool = SegmentationToolID.NoTool
