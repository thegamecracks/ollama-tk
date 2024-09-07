from __future__ import annotations

import importlib.resources
from dataclasses import dataclass
from tkinter import Event, PhotoImage
from tkinter.ttk import Frame, Label
from typing import TYPE_CHECKING, Any, Collection, Literal

from .scrollable_frame import ScrollableFrame
from .wrap_label import WrapLabel

if TYPE_CHECKING:
    from .chat import TkChat

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    content: str
    hidden: bool = False

    def dump(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content}


class TkMessageFrame(Frame):
    def __init__(
        self,
        message_list: TkMessageList,
        message: Message,
        *,
        side: Literal["left", "right"],
    ) -> None:
        super().__init__(message_list.inner)

        self.message = message
        self.message_list = message_list

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        left = side == "left"
        anchor = "w" if left else "e"

        self.role_label = Label(self, anchor=anchor, justify=side)
        self.role_label.grid(row=0, column=1, sticky="ew")

        self.role_icon = Label(self)
        self.role_icon.grid(
            row=1,
            column=0 if left else 2,
            sticky="n",
            padx=(0, 5) if left else (5, 0),
        )

        self.content_label = WrapLabel(self, anchor=anchor, justify=side)
        self.content_label.bind("<1>", self._on_content_label_click)
        self.content_label.grid(row=1, column=1, sticky="nesw")

        self.refresh()

    def refresh(self) -> None:
        role = self.message.role.title() + " (hidden)" * self.message.hidden
        self.role_label.configure(text=role)
        self.content_label.configure(text=self.message.content)

        if self.message.role == "user":
            self.role_icon.configure(image=self.message_list.icons["user"])
        else:
            self.role_icon.configure(image=self.message_list.icons["assistant"])

    def destroy(self) -> None:
        super().destroy()
        self.message_list.messages.remove(self)

    def _on_content_label_click(self, event: Event) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.content_label["text"])


class TkMessageList(ScrollableFrame):
    messages: list[TkMessageFrame]

    def __init__(self, chat: TkChat) -> None:
        super().__init__(chat, autoscroll=True, yscroll=True)

        self.chat = chat
        self.messages = []

        self.inner.grid_columnconfigure(0, weight=1)

        self.icons = load_message_icons()

    def add_message(self, message: Message) -> TkMessageFrame:
        side = "right" if message.role == "user" else "left"
        frame = TkMessageFrame(self, message, side=side)
        frame.grid(row=len(self.messages), column=0, sticky="ew")
        self.messages.append(frame)
        return frame

    def refresh(self) -> None:
        for message in self.messages:
            message.refresh()

    def clear(self) -> None:
        for message in self.messages.copy():
            message.destroy()  # NOTE: this is O(n^2)

    def dump(
        self,
        *,
        exclude: Collection[TkMessageFrame] = (),
        include_hidden: bool = False,
    ) -> list[dict[str, Any]]:
        return [
            frame.message.dump()
            for frame in self.messages
            if (include_hidden or not frame.message.hidden) and frame not in exclude
        ]


def load_message_icons() -> dict[str, PhotoImage]:
    icons = importlib.resources.files("ollamatk.icons")
    return {
        "assistant": PhotoImage(data=icons.joinpath("assistant.png").read_bytes()),
        "user": PhotoImage(data=icons.joinpath("user.png").read_bytes()),
    }
