import logging
from tkinter import Event, Menu, Tk
from tkinter.ttk import Frame

from .chat import TkChat, TkChatMenu
from .event_thread import EventThread
from .http import HTTPClient
from .logging import LogStore, TkAppLogHandler


class TkApp(Tk):
    def __init__(self, event_thread: EventThread, http: HTTPClient):
        super().__init__()

        self.event_thread = event_thread
        self.http = http
        self.logs = LogStore()

        self._connect_lifetime_with_event_thread(event_thread)

        self.title("Ollama Tk")
        self.geometry("560x670")
        self.option_add("*tearOff", False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame = TkChat(self)
        self.frame.grid(sticky="nesw")
        self.switch_menu(TkChatMenu(self))

        self.bind("<<Destroy>>", self._on_destroy)

    def switch_frame(self, frame: Frame) -> None:
        self.frame.destroy()
        self.frame = frame
        self.frame.grid(sticky="nesw")

    def switch_menu(self, menu: Menu | None) -> None:
        if menu is None:
            menu = Menu(self)

        self.configure(menu=menu)

    def listen_to_logs_from(self, logger: logging.Logger) -> TkAppLogHandler:
        handler = TkAppLogHandler(self)
        logger.addHandler(handler)
        return handler

    def _connect_lifetime_with_event_thread(self, event_thread: EventThread) -> None:
        # In our application we'll be running an asyncio event loop in
        # a separate thread. This event loop may try to run methods on
        # our GUI like event_generate(), which requires the GUI to be running.
        # If the GUI is destroyed first, it may cause a deadlock
        # in the other thread, preventing our program from exiting.
        # As such, we need to defer GUI destruction until the event thread
        # is finished.
        event_callback = lambda fut: self.event_generate("<<Destroy>>")
        event_thread.finished_fut.add_done_callback(event_callback)

    def destroy(self) -> None:
        self.event_thread.stop()

    def _on_destroy(self, event: Event) -> None:
        super().destroy()
