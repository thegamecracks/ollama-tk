import concurrent.futures
import contextlib
import functools
import logging

from .app import TkApp
from .event_thread import EventThread
from .http import HTTPClient
from .logging import configure_logging
from .styling import apply_style, enable_windows_dpi_awareness


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
        apply_style(app)

        try:
            app.mainloop()
        except BaseException:
            app.destroy()
            app.mainloop()
            raise


if __name__ == "__main__":
    main()
