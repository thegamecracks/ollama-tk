import asyncio
from typing import Any, Callable

import pytest

from ollamatk.event_thread import EventThread
from ollamatk.installable import Installable


class NullInstallable(Installable):
    events: list[Any]

    def __init__(self) -> None:
        super().__init__()
        self.events = []

    async def _install(self, ready_callback: Callable[[], asyncio.Future[Any]]) -> Any:
        self.events.append("start")
        try:
            await ready_callback()
        except BaseException as e:
            self.events.append(e)
            raise
        finally:
            self.events.append("end")


def test_installable(event_thread: EventThread) -> None:
    with NullInstallable().install(event_thread) as installable:
        assert installable.events == ["start"]
    assert installable.events == ["start", "end"]


def test_installable_exception(event_thread: EventThread) -> None:
    installable = NullInstallable()

    with pytest.raises(Exception, match="test"), installable.install(event_thread):
        raise Exception("test")

    # Exception will not propagate to _install()
    assert installable.events == ["start", "end"]


def test_repeat_installable(event_thread: EventThread) -> None:
    installable = NullInstallable()
    for _ in range(3):
        with installable.install(event_thread):
            pass
    assert installable.events == ["start", "end"] * 3


def test_double_install(event_thread: EventThread) -> None:
    with NullInstallable().install(event_thread) as installable:
        with pytest.raises(RuntimeError):
            with installable.install(event_thread):
                assert False, "double install was not blocked"
    assert installable.events == ["start", "end"]
