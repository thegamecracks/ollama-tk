from typing import Iterator

import pytest

from ollamatk.event_thread import EventThread


@pytest.fixture
def event_thread() -> Iterator[EventThread]:
    with EventThread() as event_thread:
        yield event_thread
