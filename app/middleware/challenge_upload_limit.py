from starlette.responses import JSONResponse


def private_sender(send):
    async def wrapped(message):
        if message["type"] == "http.response.start":
            headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"cache-control"]
            message = {**message, "headers": [*headers, (b"cache-control", b"private, no-store")]}
        await send(message)
    return wrapped


class ChallengeUploadLimit:
    """Bound multipart bodies before Starlette spools uploads to disk."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path", "").startswith("/api/v1/challenge-v2"):
            send = private_sender(send)
        limited = (
            scope["type"] == "http"
            and scope.get("method") == "PUT"
            and scope.get("path", "").startswith("/api/v1/challenge-v2/assignments/")
            and "/evidence/" in scope["path"]
        )
        if not limited:
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > 11 * 1024 * 1024:
                return await JSONResponse({"detail": "사진은 10MB 이하로 올려 주세요."}, status_code=413)(
                    scope, receive, send
                )
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)

        async def replay():
            nonlocal body
            if body is not None:
                message = {"type": "http.request", "body": body, "more_body": False}
                body = None
                return message
            return await receive()

        return await self.app(scope, replay, send)
