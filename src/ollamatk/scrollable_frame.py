# https://gist.github.com/thegamecracks/ee5614aa932c2167918a3c3dcc013710
from tkinter import Canvas, Event, Widget
from tkinter.ttk import Frame, Scrollbar, Style
from typing import Literal
from weakref import WeakSet


class ScrollableFrame(Frame):
    __last_scrollregion: tuple[int, int, int, int] | None

    def __init__(
        self,
        *args,
        autoscroll: bool = False,
        xscroll: bool = False,
        yscroll: bool = False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.autoscroll = autoscroll
        self.xscroll = xscroll
        self.yscroll = yscroll

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.__canvas = Canvas(self, highlightthickness=0)
        self.__canvas.grid(row=0, column=0, sticky="nesw")

        self.__xscrollbar = Scrollbar(self, orient="horizontal")
        self.__yscrollbar = Scrollbar(self, orient="vertical")

        # Use rowspan=2 or columnspan=2 appropriately if filling the
        # bottom-right corner of the frame is desired.
        self.__xscrollbar.grid(row=1, column=0, sticky="ew")
        self.__yscrollbar.grid(row=0, column=1, sticky="ns")

        self.__xscrollbar["command"] = self.__canvas.xview
        self.__yscrollbar["command"] = self.__canvas.yview
        self.__canvas["xscrollcommand"] = self.__wrap_scrollbar_set("x")
        self.__canvas["yscrollcommand"] = self.__wrap_scrollbar_set("y")

        self.inner = Frame(self.__canvas)
        self.__inner_id = self.__canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )

        self.__canvas.bind("<Configure>", lambda event: self.__update())
        self.inner.bind("<Configure>", self.__on_inner_configure)

        self.__last_scrollregion = None
        self.__last_scroll_edges = (False, False)
        self.__scrolled_widgets = WeakSet()
        self.__style = Style(self)
        self.__update_rate = 125
        self.__update_loop()

    def __on_inner_configure(self, event: Event):
        background = self.__style.lookup(self.inner.winfo_class(), "background")
        self.__canvas.configure(background=background)
        self.__update()

    def __update_loop(self):
        # Without this, any changes to the inner frame won't affect
        # the scroll bar/region until the window is resized.
        self.__update()
        self.after(self.__update_rate, self.__update_loop)

    def __update(self):
        scroll_edges = self.__get_scroll_edges()

        # self._canvas.bbox("all") doesn't update until window resize
        # so we're relying on the inner frame's requested height instead.
        new_width = self.__canvas.winfo_width()
        new_height = self.__canvas.winfo_height()
        if self.xscroll:
            new_width = max(new_width, self.inner.winfo_reqwidth())
        if self.yscroll:
            new_height = max(new_height, self.inner.winfo_reqheight())

        bbox = (0, 0, new_width, new_height)
        self.__canvas.configure(scrollregion=bbox)
        self.__canvas.itemconfigure(self.__inner_id, width=new_width, height=new_height)

        self.__update_scrollbar_visibility("x")
        self.__update_scrollbar_visibility("y")
        self.__propagate_scroll_binds(self.inner)
        self.__update_scroll_edges(bbox, *scroll_edges)
        self.__last_scroll_edges = scroll_edges

    def __get_scroll_edges(self) -> tuple[bool, bool]:
        xview = self.__canvas.xview()
        yview = self.__canvas.yview()
        scrolled_to_right = xview[1] == 1
        scrolled_to_bottom = yview[1] == 1
        return scrolled_to_right, scrolled_to_bottom

    def __propagate_scroll_binds(self, parent: Widget):
        if parent not in self.__scrolled_widgets:
            parent.bind("<MouseWheel>", self.__on_mouse_yscroll)
            parent.bind("<Shift-MouseWheel>", self.__on_mouse_xscroll)
            self.__scrolled_widgets.add(parent)

        for child in parent.winfo_children():
            self.__propagate_scroll_binds(child)

    def __update_scroll_edges(
        self,
        bbox: tuple[int, int, int, int],
        scrolled_to_right: bool,
        scrolled_to_bottom: bool,
    ) -> None:
        self.__last_scrollregion, last_bbox = bbox, self.__last_scrollregion
        if not self.autoscroll:
            return
        elif bbox == last_bbox:
            return

        if scrolled_to_right or self.__last_scroll_edges[0]:
            self.__canvas.xview_moveto(1)
        if scrolled_to_bottom or self.__last_scroll_edges[1]:
            self.__canvas.yview_moveto(1)

    def __on_mouse_xscroll(self, event: Event):
        delta = int(-event.delta / 100)
        self.__canvas.xview_scroll(delta, "units")

    def __on_mouse_yscroll(self, event: Event):
        delta = int(-event.delta / 100)
        self.__canvas.yview_scroll(delta, "units")

    def __update_scrollbar_visibility(self, axis: Literal["x", "y"]):
        scrollbar = self.__get_scrollbar_from_axis(axis)
        if scrollbar.get() == (0, 1):
            scrollbar.grid_remove()
        else:
            scrollbar.grid()

    def __wrap_scrollbar_set(self, axis: Literal["x", "y"]):
        def wrapper(*args, **kwargs):
            scrollbar.set(*args, **kwargs)
            self.__update_scrollbar_visibility(axis)

        scrollbar = self.__get_scrollbar_from_axis(axis)
        return wrapper

    def __get_scrollbar_from_axis(self, axis: Literal["x", "y"]) -> Scrollbar:
        return self.__xscrollbar if axis == "x" else self.__yscrollbar
