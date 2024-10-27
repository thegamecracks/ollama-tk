import sys
from tkinter import Tk, Toplevel as _Toplevel


class Toplevel(_Toplevel):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        apply_style(self)


def enable_windows_dpi_awareness() -> None:
    if sys.platform == "win32":
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(2)


def apply_titlebar_theme(window: Tk | _Toplevel, theme: str) -> None:
    if sys.platform != "win32":
        return

    try:
        import pywinstyles
    except ModuleNotFoundError:
        return

    version = sys.getwindowsversion()
    is_dark = theme.lower() == "dark"

    if version.major == 10 and version.build >= 22000:
        # Set the title bar color to the background color on Windows 11 for better appearance
        pywinstyles.change_header_color(window, "#1c1c1c" if is_dark else "#fafafa")
    elif version.major == 10:
        pywinstyles.apply_style(window, "dark" if is_dark else "normal")

        # A hacky way to update the title bar's color on Windows 10 (it doesn't update instantly like on Windows 11)
        window.wm_attributes("-alpha", 0.99)
        window.wm_attributes("-alpha", 1)


def apply_style(window: Tk | _Toplevel) -> None:
    try:
        import darkdetect
    except ModuleNotFoundError:
        theme = "light"
    else:
        theme = darkdetect.theme() or "light"

    try:
        import sv_ttk
    except ModuleNotFoundError:
        pass
    else:
        if isinstance(window, Tk):
            sv_ttk.set_theme(theme)

        apply_titlebar_theme(window, theme)
