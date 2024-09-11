from __future__ import annotations

import logging
from concurrent.futures import Future
from tkinter import Menu, Text
from tkinter.ttk import Button, Frame
from typing import TYPE_CHECKING, Any

import httpx

from .about import TkAboutWindow
from .http import StreamingChat
from .logging import TkLogWindow
from .messages import Message, TkMessageFrame, TkMessageList
from .settings import Settings, TkSettingsControls

if TYPE_CHECKING:
    from .app import TkApp

log = logging.getLogger(__name__)


class TkChat(Frame):
    chat_fut: Future | None
    chat_handler: StreamingChatHandler | None

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

        self.chat_handler = StreamingChatHandler(target=frame, source=source)

        coro = self.app.http.generate_chat_completion(
            address=self.settings.ollama_address,
            model=self.settings.ollama_model,
            messages=self.message_list.dump(exclude=[frame]),
            stream_callback=self.chat_handler,
            connect_callback=self.chat_handler.handle_connect,
        )

        fut = self.chat_fut = self.app.event_thread.submit(coro)
        fut.add_done_callback(self._on_send_chat_done)

        self.settings_controls.disable()
        self.live_controls.show()
        self.chat_controls.disable()

    def _on_send_chat_done(self, fut: Future[Any]) -> None:
        self.settings_controls.enable()
        self.live_controls.grid_remove()
        self.chat_controls.enable()

        assert self.chat_handler is not None
        if fut.cancelled():
            self.chat_handler.handle_cancel()
        elif (exc := fut.exception()) is not None:
            self.chat_handler.handle_error(exc)

    def maybe_get_models(self) -> None:
        # FIXME: update models any time address is changed
        if self.settings_controls.model["values"]:
            return

        coro = self.app.http.list_local_models(self.settings.ollama_address)
        fut = self.app.event_thread.submit(coro)
        fut.add_done_callback(self._on_maybe_get_models_done)

    def _on_maybe_get_models_done(self, fut: Future[list[str]]) -> None:
        if fut.cancelled():
            return
        elif fut.exception() is not None:
            return log.exception(
                "Error occurred while fetching available models",
                exc_info=fut.exception(),
            )

        self.settings_controls.model.configure(values=fut.result())


class StreamingChatHandler:
    def __init__(
        self,
        *,
        target: TkMessageFrame,
        source: TkMessageFrame | None = None,
    ) -> None:
        self.target = target
        self.source = source
        self._started = False

    def __call__(self, data: StreamingChat) -> None:
        self.target.message.role = data["message"]["role"]
        self.target.message.content += data["message"]["content"]
        self.target.refresh()

    def handle_connect(self) -> None:
        self._started = True
        self.target.message.content = ""
        self.target.refresh()

    def handle_cancel(self) -> None:
        self._show_error("(Response cancelled)")
        self._hide_messages()

    def handle_error(self, exc: BaseException) -> None:
        if isinstance(exc, httpx.ConnectError):
            self._show_error(
                "Could not connect to the given address. Is the server running?"
            )
            self._hide_messages()
        elif isinstance(exc, httpx.HTTPStatusError):
            self._handle_http_status_error(exc)
        else:
            # TODO: show more detailed error messages
            self._show_error("An unknown error occurred. Check logs for more details.")
            self._hide_messages()
            self._log_error(exc)

    def _handle_http_status_error(self, exc: httpx.HTTPStatusError) -> None:
        self._hide_messages()
        status = exc.response.status_code
        phrase = exc.response.reason_phrase

        if status == 400:
            self._show_error(f"{status} {phrase}. Did you select the model to run?")
        elif status == 404:
            self._show_error(
                f"{status} {phrase}. Maybe your selected model does not exist?"
            )
        else:
            self._show_error(f"{status} {phrase}. Check logs for more details.")
            self._log_error(exc)

    def _show_error(self, message: str) -> None:
        if self._started:
            self.target.message.content += f"...\n\n{message}"
        else:
            self.target.message.content = message
        self.target.refresh()

    def _log_error(self, exc: BaseException) -> None:
        log.exception("Error occurred while sending chat", exc_info=exc)

    def _hide_messages(self) -> None:
        # Make sure a followup chat doesn't remember the failed messages
        self.target.message.hidden = True
        self.target.refresh()
        if self.source is not None:
            self.source.message.hidden = True
            self.source.refresh()


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


class TkChatMenu(Menu):
    def __init__(self, app: TkApp) -> None:
        super().__init__(app)
        self.app = app
        self.add_command(command=lambda: TkLogWindow(app), label="Logs")
        self.add_command(command=lambda: TkAboutWindow(app), label="About")
