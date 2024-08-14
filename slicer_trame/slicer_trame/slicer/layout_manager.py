from typing import Optional

from trame_client.widgets.core import VirtualNode
from vtkmodules.vtkMRMLCore import vtkMRMLScene, vtkMRMLScriptedModuleNode

from .view_manager import ViewManager
from slicer_trame.components.layout_grid import (
    Layout,
    LayoutGrid,
    vue_layout_to_slicer,
    pretty_xml,
    slicer_layout_to_vue,
)


class LayoutManager:
    """
    Class responsible for instantiating views depending on the layout node.
        - Creates a singleton layout node at initialization.
        - Observes layout node changes to notify observers of layout id changes.
        - Can register layouts with their associated descriptions
        - Notifies view manager of requested view on layout change
    """

    def __init__(
        self,
        scene: vtkMRMLScene,
        view_manager: ViewManager,
        layout_ui_node: VirtualNode,
    ):
        self._layouts: dict[str, Layout] = {}
        self._view_manager = view_manager
        self._ui = layout_ui_node
        self._current_layout: Optional[str] = None
        self._scene_node = scene.AddNewNodeByClass(
            "vtkMRMLScriptedModuleNode", "layout_node"
        )

    def register_layout(self, layout_id, layout: Layout) -> None:
        self._layouts[layout_id] = layout
        if self._current_layout == layout_id:
            self._refresh_layout()

    def set_layout(self, layout_id: str) -> None:
        if layout_id == self._current_layout:
            return

        self._current_layout = layout_id
        self._refresh_layout()

    def _refresh_layout(self):
        layout = self._layouts.get(self._current_layout, Layout.empty_layout())
        self._create_views_if_needed(layout)
        with self._ui.clear():
            LayoutGrid.create_root_grid_ui(layout)
        self._save_layout_to_scene(self._current_layout, layout)

    def _create_views_if_needed(self, layout: Layout) -> None:
        views = layout.get_views(is_recursive=True)
        for view in views:
            if not self._view_manager.is_view_created(view.singleton_tag):
                self._view_manager.create_view(view.singleton_tag, view)

    def _save_layout_to_scene(self, layout_id: str, layout: Layout) -> None:
        self._scene_node.SetParameter("layout_id", layout_id)
        self._scene_node.SetParameter(
            "layout_description", pretty_xml(vue_layout_to_slicer(layout))
        )

    def set_layout_from_node(self, node: vtkMRMLScriptedModuleNode) -> None:
        if not node:
            raise RuntimeError("Cannot set layout from None scene node.")

        layout_id = node.GetParameter("layout_id")
        layout_description = node.GetParameter("layout_description")
        if None in [layout_id, layout_description]:
            raise RuntimeError(
                f"Invalid layout information {layout_id}, {layout_description}"
            )

        self.register_layout(layout_id, slicer_layout_to_vue(layout_description))
        self.set_layout(layout_id)

    def has_layout(self, layout_id: str) -> bool:
        return layout_id in self._layouts

    def get_layout(self, layout_id: str) -> Layout:
        if not self.has_layout(layout_id):
            raise RuntimeError(f"Layout not present in manager : {layout_id}")
        return self._layouts[layout_id]
