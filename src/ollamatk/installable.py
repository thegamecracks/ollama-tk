import asyncio
import concurrent.futures
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Self

from .event_thread import EventThread


class Installable(ABC):
    """An asynchronous resource that can be installed into an :class:`EventThread`.

    Example usage::
        resource = MyInstallable()
        with EventThread() as event_thread, resource.install(event_thread):
            resource.do_operation()
            # or:
            event_thread.submit(resource.do_async_operation())

    Subclasses must perform all set up and teardown in the asynchronous
    :meth:`_install()` method. If the :meth:`__init__()` method is overridden,
    it must explicitly call this base class's initialization.

    If asynchronous objects need to be available as attributes, it is
    recommended to use properties to validate that they are initialized.

    If an :meth:`install()` call occurs while it is already installed,
    the method will raise :exc:`RuntimeError`.

    """

    def __init__(
        self,
        *,
        ready_timeout: float | None = 5,
        stop_timeout: float | None = 5,
    ) -> None:
        super().__init__()
        self.ready_timeout = ready_timeout
        self.stop_timeout = stop_timeout
        self.__lock = threading.Lock()

    @contextmanager
    def install(self, event_thread: EventThread, /) -> Iterator[Self]:
        """Install this instance in an event thread, setting up any
        asynchronous resources.
        """

        def ready_callback() -> asyncio.Future[Any]:
            ready_fut.set_result(None)
            return asyncio.shield(asyncio.wrap_future(stop_fut))

        def cancel_task() -> None:
            nonlocal cancel_expected
            cancel_expected = True
            task_fut.cancel()

        cancel_expected = False

        with self.__installing():
            ready_fut = concurrent.futures.Future()
            stop_fut = concurrent.futures.Future()
            task_fut = event_thread.submit(self._install(ready_callback))

            try:
                done, _ = concurrent.futures.wait(
                    (task_fut, ready_fut),
                    return_when="FIRST_COMPLETED",
                    timeout=self.ready_timeout,
                )
                if ready_fut not in done:
                    if task_fut.done():
                        task_fut.result()  # propagate task exception if any
                        raise RuntimeError(
                            f"{type(self).__name__} did not invoke ready callback "
                            f"during installation"
                        )
                    else:
                        cancel_task()
                        raise TimeoutError(
                            f"{type(self).__name__} exceeded "
                            f"ready_timeout={self.ready_timeout}"
                        )

                yield self
            finally:
                stop_fut.set_result(None)
                if not cancel_expected:
                    task_fut.result(timeout=self.stop_timeout)

    @abstractmethod
    async def _install(
        self,
        ready_callback: Callable[[], asyncio.Future[Any]],
        /,
    ) -> Any:
        """Set up this class's resources and run indefinitely until cancelled.

        If an exception occurs in this coroutine, it will be propagated
        to the caller.

        If the coroutine returns without calling the ready callback,
        :exc:`RuntimeError` is raised to the caller.

        :param ready_callback:
            A function to call once initialization has finished.
            Returns a future whose result will be set once the
            instance needs to be teared down.

        """
        raise NotImplementedError

    @contextmanager
    def __installing(self) -> Iterator[Self]:
        """Acquire and hold the install lock."""
        if not self.__lock.acquire(blocking=False):
            raise RuntimeError(f"{type(self).__name__} is already installed")

        try:
            yield self
        finally:
            self.__lock.release()
