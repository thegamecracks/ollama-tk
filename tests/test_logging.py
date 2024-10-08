from ollamatk.logging import LogEventType, LogStore


def test_log_store_iterable() -> None:
    store = LogStore()

    messages = [str(i) for i in range(100)]
    for m in messages:
        store.append(m)

    assert list(store) == messages


def test_log_store_mutation_during_iteration() -> None:
    store = LogStore()
    store.append("1")

    for i, m in enumerate(store):
        store.append(m)
        if i >= 1:
            raise Exception(f"unexpected message {m!r}, possible infinite iteration?")

    assert list(store) == ["1", "1"]


def test_log_store_callbacks() -> None:
    events: list[tuple[LogEventType, str]] = []
    store = LogStore()
    store.callbacks.append(lambda type, message: events.append((type, message)))

    store.append("1")
    store.append("2")
    store.clear()

    assert events == [("insert", "1"), ("insert", "2"), ("clear", "")]


def test_log_store_clear_events_are_deduplicated() -> None:
    events: list[LogEventType] = []
    store = LogStore()
    store.callbacks.append(lambda type, message: events.append(type))

    store.clear()
    assert events == []

    store.append("")
    store.clear()
    assert events == ["insert", "clear"]

    store.clear()
    assert events == ["insert", "clear"]


def test_log_store_callback_within_callback() -> None:
    def first(type: LogEventType, message: str) -> None:
        events.append("first")
        store.callbacks.append(second)

    def second(type: LogEventType, message: str) -> None:
        events.append("second")

    events: list[str] = []
    store = LogStore()
    store.callbacks.append(first)

    store.append("")
    assert events == ["first"]

    store.append("")
    assert events == ["first", "first", "second"]
