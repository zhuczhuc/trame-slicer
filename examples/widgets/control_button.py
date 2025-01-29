from math import floor
from typing import Callable, Optional

from trame_client.widgets.html import Span
from trame_vuetify.widgets.vuetify3 import VBtn, VIcon, VTooltip


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
