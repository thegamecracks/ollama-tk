from __future__ import annotations

import logging
from contextlib import contextmanager, nullcontext
from tkinter import Text, Toplevel
from tkinter.ttk import Button, Scrollbar
from typing import TYPE_CHECKING, Any, Callable, Iterator, Literal, Self

if TYPE_CHECKING:
    from .app import TkApp

LogEventType = Literal["clear", "insert"]


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO)


class TkAppLogHandler(logging.Handler):
    def __init__(self, app: TkApp) -> None:
        super().__init__()
        self.app = app

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        self.app.logs.append(message)


class LogStore:
    callbacks: list[Callable[[LogEventType, str], Any]]
    _messages: list[str]

    def __init__(self) -> None:
        self.callbacks = []
        self._messages = []

    def __iter__(self) -> Iterator[str]:
        return iter(self._messages.copy())

    def append(self, message: str) -> None:
        self._messages.append(message)
        self._notify("insert", message)

    def clear(self) -> None:
        if len(self._messages) < 1:
            return

        self._messages.clear()
        self._notify("clear", "")

    def _notify(self, type: LogEventType, message: str) -> None:
        for callback in self.callbacks.copy():
            callback(type, message)


class TkLogWindow(Toplevel):
    def __init__(self, app: TkApp) -> None:
        super().__init__(app)

        self.app = app

        self.title("Logs")
        self.geometry("800x550")

        self.clear = Button(self, command=self.do_clear, text="Clear")
        self.clear.pack(side="bottom", anchor="e", padx=(0, 10), pady=10)

        self.text = Text(
            self,
            font="TkDefaultFont",
            width=0,
            height=0,
            state="disabled",
        )
        self.text.pack(
            side="left",
            expand=True,
            fill="both",
            padx=(10, 0),
            pady=(10, 0),
        )

        self.scrollbar = Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(expand=True, fill="y", padx=(0, 10), pady=(10, 0))

        self.refresh()
        self.app.logs.callbacks.append(self._on_log_update)

    def refresh(self) -> None:
        with self.unlock_text():
            self.text.delete("1.0", "end")
            for message in self.app.logs:
                self.text.insert("end", message + "\n")

    def do_clear(self) -> None:
        self.app.logs.clear()

    def destroy(self) -> None:
        self.app.logs.callbacks.remove(self._on_log_update)
        super().destroy()

    def _on_log_update(self, type: LogEventType, message: str) -> None:
        with self.unlock_text():
            if type == "clear":
                self.text.delete("1.0", "end")
            elif type == "insert":
                self.text.insert("end", message + "\n")

    @contextmanager
    def unlock_text(self, *, autoscroll: bool = True) -> Iterator[Self]:
        scroll_manager = self.autoscroll() if autoscroll else nullcontext()
        with scroll_manager:
            self.text.configure(state="normal")
            try:
                yield self
            finally:
                self.text.configure(state="disabled")

    @contextmanager
    def autoscroll(self) -> Iterator[Self]:
        scrolled_to_bottom = self.text.yview()[1] == 1
        try:
            yield self
        finally:
            if scrolled_to_bottom:
                self.text.yview_moveto(1)
