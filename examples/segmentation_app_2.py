from math import floor
from typing import Callable, Optional

from trame.app import get_server
from trame.decorators import TrameApp, change, trigger
from trame.widgets import vuetify3
from trame_client.widgets.html import Div, Span
from trame_vuetify.ui.vuetify3 import SinglePageLayout
from trame_vuetify.widgets.vuetify3 import (
    Template,
    VBtn,
    VCard,
    VCardText,
    VCheckboxBtn,
    VColorPicker,
    VIcon,
    VListItem,
    VMenu,
    VRadio,
    VRadioGroup,
    VRow,
    VSelect,
    VTextField,
    VTooltip,
)
from vtkmodules.vtkCommonCore import vtkCollection
from vtkmodules.vtkSegmentationCore import vtkSegmentation

from trame_slicer.core import LayoutManager, SlicerApp
from trame_slicer.rca_view import register_rca_factories
from trame_slicer.segmentation import SegmentationToolID


class ControlButton(VBtn):
    def __init__(
        self,
        *,
        name: str,
        icon: str,
        click: Optional[Callable] = None,
        size: int = 40,
        **kwargs,
    ) -> None:
        super().__init__(
            variant="text",
            rounded=0,
            height=size,
            width=size,
            min_height=size,
            min_width=size,
            click=click,
            **kwargs,
        )

        icon_size = floor(0.6 * size)

        with self:
            VIcon(icon, size=icon_size)
            with VTooltip(
                activator="parent",
                transition="slide-x-transition",
                location="right",
            ):
                Span(f"{name}")


class LayoutButton(VMenu):
    def __init__(self, layout_list):
        super().__init__(location="right", close_on_content_click=True)
        with self:
            with Template(v_slot_activator="{props}"):
                ControlButton(
                    v_bind="props",
                    icon="mdi-view-dashboard",
                    name="Layouts",
                )

            with VCard():
                with VCardText():
                    with VRadioGroup(
                        v_model="current_layout_name", classes="mt-0", hide_details=True
                    ):
                        for layout in layout_list:
                            VRadio(label=layout, value=layout)


class SegmentationButton(VMenu):
    def __init__(self):
        super().__init__(location="right", close_on_content_click=False)

        with self:
            with Template(v_slot_activator="{props}"):
                ControlButton(
                    v_bind="props",
                    icon="mdi-scissors-cutting",
                    name="Segmentation",
                )

            with VCard():
                with VCardText():
                    # Segment renaming template
                    with Template(v_if="is_renaming_segment"):
                        with VRow(align="center"):
                            VTextField(
                                model_value=("new_segment_name",),
                                update_modelValue="new_segment_name=$event;",
                                hide_details="auto",
                                width=200,
                            )
                            with VTooltip(text="Validate new name"):
                                with Template(v_slot_activator="{props}"):
                                    VBtn(
                                        icon="mdi-check",
                                        click="is_renaming_segment=false;trigger('validate_modify_segment')",
                                        v_bind="props",
                                        density="comfortable",
                                    )
                            with VTooltip(text="Cancel"):
                                with Template(v_slot_activator="{props}"):
                                    VBtn(
                                        icon="mdi-close",
                                        click="is_renaming_segment=false;",
                                        v_bind="props",
                                        density="comfortable",
                                    )
                        with VRow(align="center"):
                            VColorPicker(
                                model_value=("new_segment_color",),
                                update_modelValue="new_segment_color=$event;",
                                modes=("['rgb']",),
                            )
                    # Segment selection template
                    with Template(v_else=True):
                        with VRow(align="center"):
                            with VSelect(
                                label="Current Segment",
                                v_model="current_segment",
                                items=("segments",),
                                no_data_text="",
                                hide_details="auto",
                                min_width=200,
                            ):
                                with Template(v_slot_item="{props}"):
                                    with VListItem(v_bind="props", color=""):
                                        with Template(v_slot_prepend=""):
                                            VIcon("mdi-square", color=("props.color",))
                                with Template(v_slot_selection="{item}"):
                                    VIcon("mdi-square", color=("item.props.color",))
                                    Span("{{item.title}}", classes="pl-2")
                            with VTooltip(text="Add new segment"):
                                with Template(v_slot_activator="{props}"):
                                    VBtn(
                                        icon="mdi-plus-circle",
                                        density="comfortable",
                                        click="trigger('add_segment')",
                                        v_bind="props",
                                    )
                            with VTooltip(text="Delete current segment"):
                                with Template(v_slot_activator="{props}"):
                                    VBtn(
                                        icon="mdi-delete",
                                        density="comfortable",
                                        click="trigger('delete_segment')",
                                        v_bind="props",
                                        disabled=("!current_segment",),
                                    )
                            with VTooltip(text="Rename current segment"):
                                with Template(v_slot_activator="{props}"):
                                    VBtn(
                                        icon="mdi-rename",
                                        density="comfortable",
                                        click="is_renaming_segment=true;trigger('initiate_modify_segment')",
                                        v_bind="props",
                                        disabled=("!current_segment",),
                                    )
                        with VRow():
                            VCheckboxBtn(
                                label="Paint",
                                value="Paint",
                                v_model="segmentation_paint",
                                update_modelValue=(self.toggle_paint_mode, "[$event]"),
                                disabled=("!current_segment",),
                            )
                            VCheckboxBtn(
                                label="Erase",
                                value="Erase",
                                v_model="segmentation_erase",
                                update_modelValue=(self.toggle_erase_mode, "[$event]"),
                                disabled=("!current_segment",),
                            )

    def toggle_paint_mode(self, toggle):
        if toggle:
            self.server.state["segmentation_erase"] = False

    def toggle_erase_mode(self, toggle):
        if toggle:
            self.server.state["segmentation_paint"] = False


class ToolsStrip(Div):
    def __init__(
        self,
        *,
        layout_list,
        **kwargs,
    ):
        super().__init__(
            classes="bg-grey-darken-4 d-flex flex-column align-center", **kwargs
        )

        with self:
            LayoutButton(layout_list)
            SegmentationButton()


@TrameApp()
class MyTrameSlicerApp:
    def __init__(self, server=None, volume_file_path=None, segmentation_file_path=None):
        self._server = get_server(server, client_type="vue3")
        self._server.state.setdefault("file_loading_busy", False)

        self._slicer_app = SlicerApp()

        register_rca_factories(self._slicer_app.view_manager, self._server)

        self._layout_manager = LayoutManager(
            self._slicer_app.scene,
            self._slicer_app.view_manager,
            self._server.ui.layout_grid,
        )

        self._layout_manager.register_layout_dict(
            LayoutManager.default_grid_configuration()
        )

        self.current_volume = None
        self.current_segmentation = None
        self._segmentation = None

        self._server.controller.on_client_connected = lambda: self.load_case(
            volume_file_path, segmentation_file_path
        )

        self._build_ui()

        default_layout = "Axial Primary"
        self.server.state.setdefault("current_layout_name", default_layout)
        self._layout_manager.set_layout(default_layout)

        self.server.state.setdefault("segmentation_paint", False)
        self.server.state.setdefault("segmentation_erase", False)
        self.server.state.setdefault("is_renaming_segment", False)
        self.server.state.setdefault("segments", [])
        self.server.state.setdefault("current_segment", None)
        self.server.state.setdefault("new_segment_name", "")
        self.server.state.setdefault("new_segment_color", "")

    def _get_display_node(self):
        if self.current_volume is None:
            return None
        return self.current_volume.GetDisplayNode()

    @change("current_layout_name")
    def on_current_layout_changed(self, current_layout_name, *args, **kwargs):
        self._layout_manager.set_layout(current_layout_name)

    @change("segmentation_paint", "segmentation_erase")
    def on_segmentation_mode_changed(
        self, segmentation_paint, segmentation_erase, *args, **kwargs
    ):
        if self._segmentation is None:
            return
        if segmentation_erase:
            self._segmentation.active_tool = SegmentationToolID.PaintErase
            self._segmentation.tool.erasing = True
        elif segmentation_paint:
            self._segmentation.active_tool = SegmentationToolID.PaintErase
            self._segmentation.tool.erasing = False
        else:
            self._segmentation.active_tool = SegmentationToolID.NoTool
            self._segmentation.tool.erasing = False

    @change("current_segment")
    def on_current_segment_changed(self, current_segment, *args, **kwargs):
        if self._segmentation is None:
            return
        segment_id = None
        if current_segment is not None:
            segment_id = (
                self.current_segmentation.GetSegmentation().GetSegmentIdBySegmentName(
                    current_segment
                )
            )
        self._segmentation._editor.active_segment = segment_id

    @trigger("add_segment")
    def add_segment(self, *args, **kwargs):
        if self.current_segmentation is None:
            return
        segmentation = self.current_segmentation.GetSegmentation()
        new_segment_id = segmentation.AddEmptySegment()
        self.server.state["current_segment"] = segmentation.GetSegment(
            new_segment_id
        ).GetName()

    @trigger("delete_segment")
    def delete_segment(self, *args, **kwargs):
        if self.current_segmentation is None:
            return
        current_segment = self.server.state["current_segment"]
        segmentation = self.current_segmentation.GetSegmentation()
        segmentation.RemoveSegment(
            segmentation.GetSegmentIdBySegmentName(current_segment)
        )
        if segmentation.GetNumberOfSegments() > 0:
            segment = segmentation.GetNthSegment(0)
            current_segment = segment.GetName()
        else:
            current_segment = ""
            # If no segment remaining, use "No Tool" state
            self.server.state["segmentation_paint"] = False
            self.server.state["segmentation_erase"] = False
        self.server.state["current_segment"] = current_segment

    @trigger("initiate_modify_segment")
    def initiate_modify_segment(self, *args, **kwargs):
        if self.current_segmentation is None:
            return
        segment_name = self.server.state["current_segment"]
        self.server.state["new_segment_name"] = segment_name
        state_segments = self.server.state["segments"]
        segment_idx = [segment["title"] for segment in state_segments].index(
            segment_name
        )
        self.server.state["new_segment_color"] = self.server.state["segments"][
            segment_idx
        ]["props"]["color"]

    @trigger("validate_modify_segment")
    def validate_modify_segment(self, *args, **kwargs):
        if self.current_segmentation is None:
            return
        segmentation = self.current_segmentation.GetSegmentation()
        current_segment = self.server.state["current_segment"]
        new_name = self.server.state["new_segment_name"]
        new_color = self.server.state["new_segment_color"]
        new_color = [
            int(new_color[i + 1 : i + 3], 16) / 255.0 for i in range(0, 6, 2)
        ]  # Color uses hex format #RRGGBB
        segment = segmentation.GetSegment(
            segmentation.GetSegmentIdBySegmentName(current_segment)
        )
        segment.SetName(new_name)
        segment.SetColor(*new_color)
        self.server.state["current_segment"] = new_name

    @property
    def server(self):
        return self._server

    def _unload_nodes(self, node_class: str) -> None:
        nodes: vtkCollection = self._slicer_app.scene.GetNodesByClass(node_class)
        for i in range(nodes.GetNumberOfItems()):
            self._slicer_app.scene.RemoveNode(nodes.GetItemAsObject(i))

    def _update_state_segments(self, *args, **kwargs):
        segmentation = self.current_segmentation.GetSegmentation()
        segments = [
            segmentation.GetNthSegment(i)
            for i in range(segmentation.GetNumberOfSegments())
        ]
        segment_names = [segment.GetName() for segment in segments]
        segment_colors = []
        segment_colors = [
            "#" + "".join([f"{floor(255*c):#0{4}x}"[2:] for c in segment.GetColor()])
            for segment in segments
        ]
        self.server.state["segments"] = [
            {"title": segment_names[i], "props": {"color": segment_colors[i]}}
            for i in range(len(segments))
        ]

    def load_case(self, volume_file_path: str, segmentation_file_path: str) -> None:
        if not volume_file_path or not segmentation_file_path:
            return

        # Remove previous volume and segmentation nodes
        self._unload_nodes("vtkMRMLVolumeNode")
        self._unload_nodes("vtkMRMLSegmentationNode")

        self.current_volume = self._slicer_app.io_manager.load_volumes(
            [volume_file_path]
        )[0]
        if not self.current_volume:
            return
        if not self.current_volume:
            return
        self.current_segmentation = self._slicer_app.io_manager.load_segmentation(
            segmentation_file_path
        )
        self.current_segmentation.AddObserver(
            vtkSegmentation.SegmentAdded, self._update_state_segments
        )
        self.current_segmentation.AddObserver(
            vtkSegmentation.SegmentRemoved, self._update_state_segments
        )
        self.current_segmentation.AddObserver(
            vtkSegmentation.SegmentModified, self._update_state_segments
        )

        self._segmentation = self._slicer_app.segmentation_manager.create_segmentation(
            self.current_segmentation, self.current_volume
        )
        self._update_state_segments()
        segments = self.server.state["segments"]
        if segments:
            current_segment = segments[0]["title"]
        else:
            current_segment = None
        self.server.state["current_segment"] = current_segment

        self._slicer_app.display_manager.show_volume(
            self.current_volume,
            vr_preset="MR-Default",
            do_reset_views=True,
        )

    def _build_ui(self, *args, **kwargs):
        with SinglePageLayout(self._server) as self.ui:
            self.ui.root.theme = "dark"

            # Toolbar
            self.ui.title.set_text("Slicer Trame")

            with self.ui.toolbar:
                vuetify3.VSpacer()

            # Main content
            with self.ui.content:
                with Div(classes="fill-height d-flex flex-row flex-grow-1"):
                    ToolsStrip(
                        layout_list=self._layout_manager.get_layout_ids(),
                    )
                    self._server.ui.layout_grid(self.ui)


def main(server=None, **kwargs):
    volume_file_path = "../tests/data/mr_head.nrrd"
    segmentation_file_path = "../tests/data/segmentation.nii.gz"
    app = MyTrameSlicerApp(server, volume_file_path, segmentation_file_path)
    app.server.start(**kwargs)


if __name__ == "__main__":
    main()
