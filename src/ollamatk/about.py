from __future__ import annotations

import platform
from importlib.metadata import metadata
from tkinter import Toplevel
from tkinter.ttk import Frame, Label
from typing import TYPE_CHECKING

from .wrap_label import WrapLabel

if TYPE_CHECKING:
    from .app import TkApp


class TkAboutWindow(Toplevel):
    def __init__(self, app: TkApp) -> None:
        super().__init__(app)

        self.title("About")

        self.frame = Frame(self, padding=30)
        self.frame.pack(expand=True, fill="both")
        self.frame.grid_columnconfigure(0, weight=1)

        package = metadata("ollama-tk")

        self.name = Label(
            self.frame,
            font="Helvetica 12 bold",
            justify="center",
            text=f"OllamaTk v{package['Version']}",
        )
        self.name.grid(pady=(0, 15))

        self.description = WrapLabel(
            self.frame,
            justify="center",
            text=(
                f"By {package['Author']}\n\n"
                f"{package['Summary']}\n\n"
                f"Python version: {platform.python_version()}"
            ),
        )
        self.description.grid(pady=5)
