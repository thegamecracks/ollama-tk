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


# TODO: Reuse HTTP clients across requests.
#       These API functions can be easily wrapped in a class, but the annoying
#       part is handling the client's lifetime. This will likely involve creating
#       an asyncio task to keep the client open.
def create_httpx_client(base_url: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=base_url, timeout=10)


async def generate_chat_completion(
    *,
    target: TkMessageFrame,
    source: TkMessageFrame | None = None,
    address: str,
    model: str,
    messages: list[dict[str, Any]],
) -> None:
    def show_error(message: str) -> None:
        if append_errors:
            target.message.content += f"...\n\n{message}"
        else:
            target.message.content = message
        target.refresh()

    def hide_source() -> None:
        # Make sure a followup chat doesn't remember the last message that failed
        if source is not None:
            source.message.hidden = True
            source.refresh()

    if not target.message.hidden:
        raise ValueError("target message must be initially hidden")

    payload = {"model": model, "messages": messages}
    append_errors = False

    try:
        async with (
            create_httpx_client(address) as client,
            client.stream("POST", "/api/chat", json=payload) as response,
        ):
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

    except httpx.ConnectError:
        show_error("Could not connect to the given address. Is the server running?")
        hide_source()
    except Exception:
        # TODO: show more detailed error messages
        show_error("An unknown error occurred. Please try again.")
        hide_source()
        raise
    else:
        target.message.hidden = False
        target.refresh()


async def list_local_models(address: str) -> list[str]:
    async with create_httpx_client(address) as client:
        response = await client.get("/api/tags")
        response.raise_for_status()
        return [model["name"] for model in response.json()["models"]]
