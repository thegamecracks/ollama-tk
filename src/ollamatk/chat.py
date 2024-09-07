from __future__ import annotations

from tkinter import Text
from tkinter.ttk import Button, Frame
from typing import TYPE_CHECKING

from .messages import Message, TkMessageList
from .settings import Settings, TkSettingsControls

if TYPE_CHECKING:
    from .app import TkApp


class TkChat(Frame):
    def __init__(self, app: TkApp) -> None:
        super().__init__(app)

        self.app = app

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=7)
        self.grid_rowconfigure(2, weight=1)

        self.settings = Settings()

        self.settings_controls = TkSettingsControls(self, self.settings)
        self.settings_controls.grid(row=0, column=0, sticky="e", padx=10, pady=(10, 0))

        self.message_list = TkMessageList(self)
        self.message_list.grid(row=1, column=0, sticky="nesw", padx=10, pady=10)

        self.chat_controls = TkChatControls(self)
        self.chat_controls.grid(row=2, column=0, sticky="nesw", padx=10, pady=(0, 10))


class TkChatControls(Frame):
    def __init__(self, chat: TkChat) -> None:
        super().__init__(chat)

        self.chat = chat

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.text = Text(self, font="TkDefaultFont", width=50, height=4)
        self.text.grid(row=0, column=0, sticky="nesw", padx=(0, 20))
        self._init_text_bindings()

        self.buttons = TkChatButtons(self)
        self.buttons.grid(row=0, column=1, sticky="ns")

    def disable(self) -> None:
        self.text.configure(state="disabled")
        self.buttons.disable()

    def enable(self) -> None:
        self.text.configure(state="normal")
        self.buttons.enable()

    def _init_text_bindings(self) -> None:
        self.text.bind("<Shift-Return>", lambda event: self.text.insert("insert", "\n"))
        self.text.unbind_all("<Return>")
        self.text.bind("<Return>", lambda event: self.buttons.do_send())


class TkChatButtons(Frame):
    def __init__(self, controls: TkChatControls) -> None:
        super().__init__(controls)

        self.controls = controls

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure("0 1", weight=1)

        self.send_button = Button(self, command=self.do_send, text="Send")
        self.send_button.grid(row=0, column=0, sticky="new")

        self.clear_button = Button(self, command=self.do_clear, text="Clear")
        self.clear_button.grid(row=1, column=0, sticky="sew")

    def do_send(self) -> None:
        content = self.controls.text.get("1.0", "end").strip()
        if content == "":
            return

        message = Message("user", content)
        self.controls.chat.message_list.add_message(message)
        self.controls.text.delete("1.0", "end")
        # TODO: disable controls and perform I/O, include timeout

    def do_clear(self) -> None:
        self.controls.chat.message_list.clear()

    def disable(self) -> None:
        self.send_button.state(["disabled"])
        self.clear_button.state(["disabled"])

    def enable(self) -> None:
        self.send_button.state(["!disabled"])
        self.clear_button.state(["!disabled"])
