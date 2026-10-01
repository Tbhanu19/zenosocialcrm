"""Response headers that do not depend on a reverse proxy."""

from collections.abc import Awaitable, Callable, MutableMapping

Scope = MutableMapping[str, object]
Message = MutableMapping[str, object]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


class SecurityHeadersMiddleware:
    """Add framing and content-type protections to every HTTP response."""

    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message.get("type") == "http.response.start":
                raw_headers = message.get("headers")
                headers = list(raw_headers) if isinstance(raw_headers, list) else []
                headers.extend(
                    (
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"x-frame-options", b"DENY"),
                    )
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
