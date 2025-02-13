import concurrent.futures
import contextlib
import functools
import logging
import sys

from .app import TkApp
from .event_thread import EventThread
from .http import HTTPClient
from .logging import configure_logging


def suppress(*exceptions: type[BaseException]):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with contextlib.suppress(*exceptions):
                return func(*args, **kwargs)

        return wrapper

    return decorator


@suppress(KeyboardInterrupt, concurrent.futures.CancelledError)
def main() -> None:
    configure_logging()
    enable_windows_dpi_awareness()

    event_thread = EventThread()
    http = HTTPClient()
    with event_thread, http.install(event_thread):
        app = TkApp(event_thread, http)
        app.listen_to_logs_from(logging.getLogger())

        try:
            app.mainloop()
        except BaseException:
            app.destroy()
            app.mainloop()
            raise


def enable_windows_dpi_awareness() -> None:
    if sys.platform == "win32":
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(2)


if __name__ == "__main__":
    main()
