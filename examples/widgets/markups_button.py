from trame_slicer.core import SlicerApp

from .control_button import ControlButton


class MarkupsButton(ControlButton):
    def __init__(self, server, slicer_app: SlicerApp):
        super().__init__(
            name="Place Points",
            icon="mdi-dots-square",
            click=self.on_markups_clicked,
        )
        self._slicer_app = slicer_app
        self._server = server
        self._markups_node = None

    def on_markups_clicked(self):
        if self._markups_node is None:
            self._markups_node = self._slicer_app.scene.AddNewNodeByClass(
                "vtkMRMLMarkupsFiducialNode"
            )

        self._slicer_app.markups_logic.SetActiveList(self._markups_node)
        self._slicer_app.markups_logic.StartPlaceMode(True)
