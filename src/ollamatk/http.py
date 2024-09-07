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


async def generate_chat_completion(
    *,
    target: TkMessageFrame,
    source: TkMessageFrame | None = None,
    address: str,
    model: str,
    messages: list[dict[str, Any]],
) -> None:
    if not target.message.hidden:
        raise ValueError("target message must be initially hidden")

    payload = {"model": model, "messages": messages}
    append_errors = False

    try:
        # TODO: reuse HTTP client
        async with (
            httpx.AsyncClient(base_url=address, timeout=10) as client,
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

    except Exception:
        # TODO: show more detailed error messages
        if append_errors:
            target.message.content += (
                "...\n\nAn error occurred on the server. Please try again."
            )
        else:
            target.message.content = (
                "An error occurred while sending the request. Please try again."
            )
        target.refresh()

        if source is not None:
            # Make sure a followup chat doesn't remember the last message that failed
            source.message.hidden = True
            source.refresh()

        raise
    else:
        target.message.hidden = False
        target.refresh()
