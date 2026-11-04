"""Public (token-scoped) serving of a generated app: /preview/{token}/...

No session cookie is involved: the unguessable token *is* the capability, and the
responses carry a CSP sandbox so the page runs in an opaque origin even when
opened outside the DevTeam iframe.
"""

import mimetypes

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse

from app.ai_core.execution.preview import previews

router = APIRouter(prefix="/preview", tags=["preview"])

# The project contract makes generated frontends call this backend address
GENERATED_API_BASES = ("http://localhost:8001", "http://127.0.0.1:8001")
# No frame-ancestors here: under `sandbox` the document's own origin is opaque, so
# 'self' would match nothing and block DevTeam from embedding it. Framing is limited
# by nginx's X-Frame-Options: SAMEORIGIN instead (checked against the URL's origin).
SANDBOX_CSP = "sandbox allow-scripts allow-forms allow-modals"
CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}
HOP_HEADERS = {"connection", "keep-alive", "transfer-encoding", "content-encoding", "content-length", "server", "date"}
MAX_BODY = 1_000_000


def _not_found() -> Response:
    return PlainTextResponse("Bản xem trước không tồn tại hoặc đã hết hạn", status_code=404)


@router.api_route("/{token}/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_api(token: str, path: str, request: Request) -> Response:
    preview = previews.by_token(token)
    if preview is None:
        return _not_found()
    if request.method == "OPTIONS":
        return Response(status_code=204, headers=CORS)
    if not preview.api_running:
        return PlainTextResponse("Backend của ứng dụng không chạy", status_code=502, headers=CORS)
    body = await request.body()
    if len(body) > MAX_BODY:
        return PlainTextResponse("Request quá lớn", status_code=413, headers=CORS)
    headers = {k: v for k, v in request.headers.items() if k.lower() in ("content-type", "accept")}
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            upstream = await client.request(request.method, f"http://127.0.0.1:{preview.port}/{path}",
                                            params=request.query_params, content=body, headers=headers)
        except httpx.HTTPError as exc:
            return PlainTextResponse(f"Không kết nối được backend của ứng dụng: {type(exc).__name__}",
                                     status_code=502, headers=CORS)
    out = {k: v for k, v in upstream.headers.items()
           if k.lower() not in HOP_HEADERS and not k.lower().startswith("access-control-")}
    return Response(upstream.content, status_code=upstream.status_code, headers={**out, **CORS})


@router.get("/{token}/{path:path}")
def serve_frontend(token: str, path: str) -> Response:
    preview = previews.by_token(token)
    if preview is None:
        return _not_found()
    base = (preview.root / "frontend").resolve()
    target = (base / (path or "index.html")).resolve()
    if not target.is_relative_to(base):  # path traversal
        return _not_found()
    if target.is_dir():
        target = target / "index.html"
    if not target.is_file() or target.is_symlink():
        return _not_found()
    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    content = target.read_bytes()
    if target.suffix.lower() in (".html", ".js", ".mjs", ".css"):
        text = content.decode("utf-8", errors="replace")
        for base_url in GENERATED_API_BASES:
            text = text.replace(base_url, f"/preview/{token}/api")
        content = text.encode("utf-8")
        media_type += "; charset=utf-8"
    return Response(content, media_type=media_type, headers={
        "Content-Security-Policy": SANDBOX_CSP,
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
        **CORS,
    })
