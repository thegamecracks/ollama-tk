import asyncio
import json
from typing import Any, Literal, TypedDict, cast

import httpx

from .messages import Role, TkMessageFrame


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
        target: TkMessageFrame,
        source: TkMessageFrame | None = None,
        address: httpx.URL | str,
        model: str,
        messages: list[dict[str, Any]],
    ) -> None:
        def show_error(message: str) -> None:
            if append_errors:
                target.message.content += f"...\n\n{message}"
            else:
                target.message.content = message
            target.refresh()

        def hide_messages() -> None:
            # Make sure a followup chat doesn't remember the failed messages
            target.message.hidden = True
            target.refresh()
            if source is not None:
                source.message.hidden = True
                source.refresh()

        address = httpx.URL(address).join("/api/chat")
        payload = {"model": model, "messages": messages}
        append_errors = False

        try:
            async with self.client.stream("POST", address, json=payload) as response:
                response.raise_for_status()

                append_errors = True
                target.message.content = ""
                target.refresh()

                async for line in response.aiter_lines():  # NOTE: what if this hangs?
                    data = cast(StreamingChat | DoneStreamingChat, json.loads(line))

                    error = data.get("error")
                    if error is not None:
                        raise RuntimeError(error)

                    if not data.get("done"):
                        data = cast(StreamingChat, data)
                        target.message.role = data["message"]["role"]
                        target.message.content += data["message"]["content"]
                    else:
                        data = cast(DoneStreamingChat, data)
                        # Nothing to do here really

                    target.refresh()

        except asyncio.CancelledError:
            show_error("(Response cancelled)")
            hide_messages()
            raise
        except httpx.ConnectError:
            show_error("Could not connect to the given address. Is the server running?")
            hide_messages()
        except httpx.HTTPStatusError as e:
            hide_messages()
            status = e.response.status_code
            phrase = e.response.reason_phrase

            if status == 400:
                show_error(f"{status} {phrase}. Did you select the model to run?")
            elif status == 404:
                show_error(
                    f"{status} {phrase}. Maybe your selected model does not exist?"
                )
            else:
                show_error(f"{status} {phrase}. Check logs for more details.")
                raise

        except Exception:
            # TODO: show more detailed error messages
            show_error("An unknown error occurred. Check logs for more details.")
            hide_messages()
            raise

    async def list_local_models(self, address: httpx.URL | str) -> list[str]:
        address = httpx.URL(address).join("/api/tags")
        response = await self.client.get(address)
        response.raise_for_status()
        return [model["name"] for model in response.json()["models"]]
