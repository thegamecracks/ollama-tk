import contextlib
import functools
import sys

from .app import TkApp
from .event_thread import EventThread


def suppress(*exceptions: type[BaseException]):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with contextlib.suppress(*exceptions):
                return func(*args, **kwargs)
        return wrapper
    return decorator


@suppress(KeyboardInterrupt)
def main() -> None:
    enable_windows_dpi_awareness()

    with EventThread() as event_thread:
        app = TkApp(event_thread)

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
