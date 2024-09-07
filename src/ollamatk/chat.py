from __future__ import annotations

from concurrent.futures import Future
from tkinter import Text
from tkinter.ttk import Button, Frame
from typing import TYPE_CHECKING, Any

from .http import generate_chat_completion, list_local_models
from .messages import Message, TkMessageFrame, TkMessageList
from .settings import Settings, TkSettingsControls

if TYPE_CHECKING:
    from .app import TkApp


class TkChat(Frame):
    chat_fut: Future | None

    def __init__(self, app: TkApp) -> None:
        super().__init__(app)

        self.app = app

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=7)
        self.grid_rowconfigure(3, weight=1)

        self.settings = Settings()

        self.settings_controls = TkSettingsControls(self, self.settings)
        self.settings_controls.grid(row=0, column=0, sticky="e", padx=10, pady=(10, 0))

        self.message_list = TkMessageList(self)
        self.message_list.grid(row=1, column=0, sticky="nesw", padx=10, pady=(10, 0))

        self.live_controls = TkLiveControls(self)
        self.live_controls.grid(row=2, column=0, sticky="w", padx=10, pady=(10, 0))
        self.live_controls.grid_remove()  # Show later when necessary

        self.chat_controls = TkChatControls(self)
        self.chat_controls.grid(row=3, column=0, sticky="nesw", padx=10, pady=10)

        self.chat_fut = None

    def send_chat(self, *, source: TkMessageFrame | None) -> None:
        message = Message("assistant", "Waiting for response...")
        frame = self.message_list.add_message(message)

        coro = generate_chat_completion(
            target=frame,
            source=source,
            address=self.settings.ollama_address,
            model=self.settings.ollama_model,
            messages=self.message_list.dump(),
        )

        fut = self.chat_fut = self.app.event_thread.submit(coro)
        fut.add_done_callback(self._on_send_chat_done)

        self.settings_controls.disable()
        self.chat_controls.disable()
        self.live_controls.show()

    def _on_send_chat_done(self, fut: Future[Any]) -> None:
        self.settings_controls.enable()
        self.live_controls.grid_remove()
        self.chat_controls.enable()

        if not fut.cancelled():
            fut.result()  # If an error occurred, print it

    def maybe_get_models(self) -> None:
        # FIXME: update models any time address is changed
        if self.settings_controls.model["values"]:
            return

        coro = list_local_models(address=self.settings.ollama_address)
        fut = self.app.event_thread.submit(coro)
        fut.add_done_callback(self._on_maybe_get_models_done)

    def _on_maybe_get_models_done(self, fut: Future[list[str]]) -> None:
        if fut.cancelled() or fut.exception():
            return

        self.settings_controls.model.configure(values=fut.result())


class TkLiveControls(Frame):
    def __init__(self, chat: TkChat) -> None:
        super().__init__(chat)

        self.chat = chat

        self.grid_columnconfigure(0, weight=1)

        self.cancel = Button(self, command=self.do_cancel, text="Cancel")
        self.cancel.grid(row=0, column=0)

    def do_cancel(self) -> None:
        if self.chat.chat_fut is not None:
            self.chat.chat_fut.cancel()
            self.cancel.state(["disabled"])

    def show(self) -> None:
        self.cancel.state(["!disabled"])
        self.grid()


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
        self.text.bind("<Shift-Return>", lambda event: self.text.insert("insert", ""))
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
        message = self.controls.chat.message_list.add_message(message)
        self.controls.text.delete("1.0", "end")
        self.controls.chat.send_chat(source=message)
        self.controls.chat.maybe_get_models()

    def do_clear(self) -> None:
        self.controls.chat.message_list.clear()

    def disable(self) -> None:
        self.send_button.state(["disabled"])
        self.clear_button.state(["disabled"])

    def enable(self) -> None:
        self.send_button.state(["!disabled"])
        self.clear_button.state(["!disabled"])
