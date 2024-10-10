import asyncio
import collections
import concurrent.futures
from typing import Any, Callable, Hashable, TypeVar

import pytest

from ollamatk.event_thread import EventThread

T = TypeVar("T")


class InfiniteTask:
    events: list[Any]
    _event_callbacks: dict[Hashable, list[Callable[[], Any]]]

    def __init__(self) -> None:
        self.events = []
        self._event_callbacks = collections.defaultdict(list)

    async def start(self) -> None:
        self._dispatch("start")
        try:
            await asyncio.get_running_loop().create_future()
        except BaseException as e:
            self._dispatch(e)
            raise
        finally:
            self._dispatch("end")

    def create_future_for_event(self, value: Hashable) -> concurrent.futures.Future[None]:
        def callback() -> None:
            fut.set_result(None)
            self._event_callbacks[value].remove(callback)

        fut = concurrent.futures.Future()
        self._event_callbacks[value].append(lambda: fut.set_result(None))
        return fut

    def _dispatch(self, value: Hashable) -> None:
        self.events.append(value)
        for callback in self._event_callbacks[value].copy():
            callback()


def test_event_thread_start_and_stop() -> None:
    with EventThread() as event_thread:
        loop = event_thread.loop_fut.result(timeout=0)
        assert loop.is_running()
    assert loop.is_closed()


def test_event_thread_submit() -> None:
    value = 123
    with EventThread() as event_thread:
        fut = event_thread.submit(asyncio.sleep(0, value))
        assert fut.result(timeout=1) == value


def test_event_thread_exits_after_exception() -> None:
    task = InfiniteTask()

    with pytest.raises(Exception, match="test"), EventThread() as event_thread:
        start_fut = task.create_future_for_event("start")
        task_fut = event_thread.submit(task.start())
        start_fut.result(timeout=1)

        raise Exception("test")

    loop = event_thread.loop_fut.result(timeout=0)
    assert loop.is_closed()

    assert len(task.events) == 3
    assert task.events[0] == "start"
    assert isinstance(task.events[1], asyncio.CancelledError)
    assert task_fut.cancelled()  # type: ignore  # should always be defined
    assert task.events[2] == "end"
