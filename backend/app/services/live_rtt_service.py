# Realtime transcription bridge: browser WebSocket → VALSEA RTT WebSocket → browser.
import asyncio
import json
import time
from contextlib import suppress
from typing import Any

import websockets
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.config import settings
from app.services.pipeline import process_transcript


async def live_transcription_session(client_ws: WebSocket) -> None:
    """
    Nhận audio PCM16 base64 từ frontend, gửi tới VALSEA RTT, stream partial/final transcript về UI.
    Khi client gửi stop, gom final transcript và sinh full study pack bằng pipeline hiện có.
    """
    await client_ws.accept()
    if not (settings.valsea_api_key or "").strip():
        await client_ws.send_json(
            {
                "type": "error",
                "message": "Thiếu VALSEA_API_KEY trong backend/.env nên không chạy realtime được.",
            }
        )
        await client_ws.close(code=1008)
        return

    rtt_url = settings.valsea_base_resolved().replace("https://", "wss://").replace("http://", "ws://")
    rtt_url = f"{rtt_url}/v1/realtime"
    headers = {"Authorization": f"Bearer {settings.valsea_api_key.strip()}"}
    final_segments: list[str] = []
    bookmarks: list[dict[str, Any]] = []
    latest_partial = ""
    started_at = time.monotonic()
    stop_event = asyncio.Event()
    rtt_ready = False
    pending_audio: list[str] = []

    try:
        valsea_ws = await _connect_valsea_ws(rtt_url, headers)
    except Exception as e:  # websockets wraps network/auth failures in several exception types.
        await client_ws.send_json({"type": "error", "message": f"Không kết nối được VALSEA RTT: {e!s}"})
        await client_ws.close(code=1011)
        return

    try:
        await valsea_ws.send(
            json.dumps(
                {
                    "type": "session.start",
                    "model": "valsea-rtt",
                    "language": (settings.valsea_language or "vietnamese").strip().lower(),
                    "enable_correction": settings.valsea_enable_correction,
                    "hint_text": "University lecture, EdTech, bilingual Vietnamese and English.",
                },
                ensure_ascii=False,
            )
        )
        await client_ws.send_json({"type": "status", "status": "connecting", "message": "Đang mở VALSEA RTT…"})

        async def from_valsea() -> None:
            nonlocal latest_partial, rtt_ready
            async for raw in valsea_ws:
                event = _loads(raw)
                etype = event.get("type", "")
                if etype == "session.ready":
                    rtt_ready = True
                    # Flush các chunk audio đã tới trong lúc engine đang khởi động.
                    while pending_audio:
                        audio = pending_audio.pop(0)
                        await valsea_ws.send(json.dumps({"type": "audio.append", "audio": audio}))
                    await client_ws.send_json({"type": "status", "status": "ready", "message": "Realtime ready"})
                elif etype == "session.created":
                    await client_ws.send_json({"type": "status", "status": "created", "session": event})
                elif etype == "transcript.partial":
                    latest_partial = event.get("text", "") or ""
                    await client_ws.send_json(
                        {
                            "type": "partial",
                            "text": latest_partial,
                            "timestampMs": event.get("timestampMs"),
                        }
                    )
                elif etype == "transcript.final":
                    text = event.get("text") or event.get("raw_text") or ""
                    if text.strip():
                        final_segments.append(text.strip())
                    latest_partial = ""
                    await client_ws.send_json(
                        {
                            "type": "final",
                            "text": text,
                            "raw_text": event.get("raw_text", ""),
                            "timestampMs": event.get("timestampMs"),
                            "corrections": event.get("corrections", []),
                            "live_note": _live_note_from_text(text),
                        }
                    )
                elif etype == "error":
                    await client_ws.send_json({"type": "error", "message": event.get("message", "VALSEA RTT error")})
                else:
                    await client_ws.send_json({"type": "rtt_event", "event": event})

        async def from_client() -> None:
            nonlocal latest_partial
            while True:
                try:
                    msg = await client_ws.receive_json()
                except WebSocketDisconnect:
                    stop_event.set()
                    break
                mtype = msg.get("type")
                if mtype == "audio":
                    audio = msg.get("audio")
                    if audio:
                        if rtt_ready:
                            await valsea_ws.send(json.dumps({"type": "audio.append", "audio": audio}))
                        else:
                            # VALSEA báo lỗi nếu audio.append trước session.ready.
                            # Giữ queue ngắn để tránh phình RAM nếu client nói ngay từ đầu.
                            pending_audio.append(audio)
                            if len(pending_audio) > 80:
                                pending_audio.pop(0)
                elif mtype == "commit":
                    await valsea_ws.send(json.dumps({"type": "audio.commit"}))
                elif mtype == "bookmark":
                    mark = {
                        "id": f"bm-{len(bookmarks) + 1}",
                        "elapsedSec": round(time.monotonic() - started_at, 1),
                        "label": msg.get("label") or "Bookmark",
                        "text": latest_partial or (final_segments[-1] if final_segments else ""),
                    }
                    bookmarks.append(mark)
                    await client_ws.send_json({"type": "bookmark", "bookmark": mark})
                elif mtype == "stop":
                    with suppress(Exception):
                        await valsea_ws.send(json.dumps({"type": "audio.commit"}))
                        await valsea_ws.send(json.dumps({"type": "session.stop"}))
                    stop_event.set()
                    break

        vtoc = asyncio.create_task(from_valsea())
        ctov = asyncio.create_task(from_client())
        await stop_event.wait()
        # Cho VALSEA thêm một chút thời gian để gửi final segment cuối sau audio.commit.
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(vtoc, timeout=1.25)
        for task in (vtoc, ctov):
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
    finally:
        with suppress(Exception):
            await valsea_ws.close()

    transcript = " ".join(final_segments).strip()
    await _send_study_pack(client_ws, transcript, bookmarks)


async def _connect_valsea_ws(url: str, headers: dict[str, str]):
    """Tương thích websockets 14+ (`additional_headers`) và bản cũ (`extra_headers`)."""
    try:
        return await websockets.connect(url, additional_headers=headers)
    except TypeError:
        return await websockets.connect(url, extra_headers=headers)


async def _send_study_pack(client_ws: WebSocket, transcript: str, bookmarks: list[dict[str, Any]]) -> None:
    """Sinh study pack cuối buổi và gửi về frontend."""
    if not transcript:
        await client_ws.send_json(
            {
                "type": "study_pack_error",
                "message": "Chưa có final transcript để tạo flashcards/quiz. Hãy nói lâu hơn hoặc kiểm tra mic.",
                "bookmarks": bookmarks,
            }
        )
        await client_ws.close()
        return

    await client_ws.send_json({"type": "status", "status": "processing", "message": "Đang tạo flashcards/quiz…"})
    result = await process_transcript(transcript)
    await client_ws.send_json(
        {
            "type": "study_pack",
            "result": result.model_dump(mode="json"),
            "bookmarks": bookmarks,
        }
    )
    await client_ws.close()


def _loads(raw: str | bytes) -> dict[str, Any]:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {"type": "message", "value": data}
    except json.JSONDecodeError:
        return {"type": "message", "text": str(raw)}


def _live_note_from_text(text: str) -> str:
    """Tạo note live ngắn ngay khi final segment về, để UI có cảm giác trợ giảng realtime."""
    t = " ".join((text or "").split())
    if not t:
        return ""
    if len(t) <= 140:
        return t
    return t[:137].rstrip() + "..."
