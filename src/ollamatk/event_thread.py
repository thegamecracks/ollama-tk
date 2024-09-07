# https://gist.github.com/thegamecracks/564bd55af973827f8a05b48f197d5c09
import asyncio
import concurrent.futures
import threading
from typing import Any, Coroutine, Self, TypeVar

T = TypeVar("T")


class EventThread(threading.Thread):
    """Runs an asyncio event loop in a separate thread.
    Starting and stopping can be done with :meth:`start()` and :meth:`stop()`,
    but for reliability, you should use the class in a context manager instead::
        >>> with EventThread() as event_thread:
        ...     loop = event_thread.loop
        ...     future = asyncio.run_coroutine_threadsafe(my_task(), loop)
        ...     result = future.result()
        >>> # Event loop will be cleaned up before exiting
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.loop_fut = concurrent.futures.Future()
        self.stop_fut = concurrent.futures.Future()
        self.finished_fut = concurrent.futures.Future()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, tb) -> None:
        self.stop()
        self.join()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self.loop_fut.result()

    def run(self) -> None:
        try:
            asyncio.run(self._run_forever())
        finally:
            self.finished_fut.set_result(None)

    def submit(self, coro: Coroutine[Any, Any, T]) -> concurrent.futures.Future[T]:
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self) -> None:
        try:
            self.stop_fut.set_result(None)
        except concurrent.futures.InvalidStateError:
            pass

    async def _run_forever(self) -> None:
        self.loop_fut.set_result(asyncio.get_running_loop())
        await asyncio.wrap_future(self.stop_fut)
