import asyncio
import json
from typing import Any, Callable, Literal, TypedDict, cast

import httpx

from .messages import Role


# https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion
class Message(TypedDict):
    role: Role
    content: str
    images: list[str] | None


class StreamingChat(TypedDict):
    model: str
    created_at: str
    message: Message
    done: Literal[False]


class DoneStreamingChat(TypedDict):
    model: str
    created_at: str
    done: Literal[True]
    total_duration: int  # in nanoseconds
    load_duration: int  # in nanoseconds
    prompt_eval_count: int
    prompt_eval_duration: int  # in nanoseconds
    eval_count: int
    eval_duration: int  # in nanoseconds


class HTTPClient:
    _client: httpx.AsyncClient | None

    def __init__(self) -> None:
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("HTTPClient is not running")
        return self._client

    async def run(self) -> None:
        if self._client is not None:
            raise RuntimeError("HTTPClient is already running")

        self._client = httpx.AsyncClient(timeout=10)
        try:
            async with self._client:
                await asyncio.get_running_loop().create_future()
        finally:
            self._client = None

    async def generate_chat_completion(
        self,
        *,
        address: httpx.URL | str,
        model: str,
        messages: list[dict[str, Any]],
        stream_callback: Callable[[StreamingChat], Any],
        connect_callback: Callable[[], Any] = lambda: True,
    ) -> None:
        address = httpx.URL(address).join("/api/chat")
        payload = {"model": model, "messages": messages}

        async with self.client.stream("POST", address, json=payload) as response:
            response.raise_for_status()
            connect_callback()
            async for line in response.aiter_lines():  # NOTE: what if this hangs?
                data = cast(StreamingChat | DoneStreamingChat, json.loads(line))

                error = data.get("error")
                if error is not None:
                    raise RuntimeError(error)

                if not data.get("done"):
                    data = cast(StreamingChat, data)
                    stream_callback(data)
                else:
                    data = cast(DoneStreamingChat, data)
                    # Nothing to do here really

    async def list_local_models(self, address: httpx.URL | str) -> list[str]:
        address = httpx.URL(address).join("/api/tags")
        response = await self.client.get(address)
        response.raise_for_status()
        return [model["name"] for model in response.json()["models"]]
