# Enrichment layer dùng các endpoint text của VALSEA sau khi đã có transcript.
import asyncio
import json
import logging
import re
from typing import Any

import httpx

from app.config import settings
from app.schemas import FormattedNotes

logger = logging.getLogger(__name__)


def has_valsea_key() -> bool:
    """Kiểm tra key một lần để pipeline biết có nên gọi enrichment thật không."""
    return bool((settings.valsea_api_key or "").strip())


async def enrich_transcript(transcript: str, summary: str) -> dict[str, Any]:
    """
    Gọi các endpoint text của VALSEA:
    - Clarify: làm sạch transcript nói tự nhiên.
    - Annotate: semantic tags / corrections.
    - Formatting: lecture notes, action items, key quotes.
    - Translate: tạo summary tiếng Anh (hoặc target trong env).

    Các bước này là phụ trợ: nếu một bước lỗi, pipeline vẫn trả kết quả chính.
    """
    if not has_valsea_key() or not settings.valsea_enable_enrichment:
        return _fallback_enrichment(transcript, summary)

    warnings: list[str] = []
    base = settings.valsea_base_resolved()
    headers = {
        "Authorization": f"Bearer {settings.valsea_api_key.strip()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=180.0, headers=headers) as client:
        clarify_task = _safe_call(
            "clarify",
            _clarify(client, base, transcript),
            warnings,
        )
        annotate_task = _safe_call(
            "annotate",
            _annotate(client, base, transcript),
            warnings,
        )
        notes_task = _safe_call(
            "lecture notes",
            _format(client, base, transcript, "meeting_minutes"),
            warnings,
        )
        actions_task = _safe_call(
            "action items",
            _format(client, base, transcript, "action_items"),
            warnings,
        )
        quotes_task = _safe_call(
            "key quotes",
            _format(client, base, transcript, "key_quotes"),
            warnings,
        )
        translate_task = _safe_call(
            "translate",
            _translate(client, base, summary, settings.valsea_translate_target),
            warnings,
        )
        clarified, annotated, notes, actions, quotes, translated = await asyncio.gather(
            clarify_task,
            annotate_task,
            notes_task,
            actions_task,
            quotes_task,
            translate_task,
        )

    fallback = _fallback_enrichment(transcript, summary)
    formatted_notes = FormattedNotes(
        lecture_notes=_extract_lines(notes) or fallback["formatted_notes"].lecture_notes,
        action_items=_extract_lines(actions) or fallback["formatted_notes"].action_items,
        key_quotes=_extract_lines(quotes) or fallback["formatted_notes"].key_quotes,
    )
    semantic_tags = _extract_semantic_tags(annotated)

    bilingual = {
        "vietnamese": summary,
    }
    if translated:
        bilingual[settings.valsea_translate_target] = translated

    return {
        "clarified_transcript": clarified or fallback["clarified_transcript"],
        "semantic_tags": semantic_tags,
        "formatted_notes": formatted_notes,
        "bilingual_summary": bilingual,
        "enrichment_warnings": warnings,
    }


async def _safe_call(name: str, coro, warnings: list[str]):
    """Bọc từng API call để lỗi phụ không làm hỏng toàn bộ pipeline học tập."""
    try:
        return await coro
    except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("VALSEA %s enrichment failed: %s", name, e)
        warnings.append(f"VALSEA {name} chưa trả được kết quả: {e!s}")
        return None


async def _clarify(client: httpx.AsyncClient, base: str, text: str) -> str:
    resp = await client.post(
        f"{base}/v1/clarifications",
        json={
            "model": "valsea-clarify",
            "text": text,
            "language": (settings.valsea_language or "vietnamese").strip().lower(),
            "response_format": "json",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("clarified_text") or data.get("text") or ""


async def _annotate(client: httpx.AsyncClient, base: str, text: str) -> dict[str, Any]:
    resp = await client.post(
        f"{base}/v1/annotations",
        json={
            "model": "valsea-annotate",
            "text": text,
            "language": (settings.valsea_language or "vietnamese").strip().lower(),
            "response_format": "verbose_json",
            "enable_correction": settings.valsea_enable_correction,
            "enable_tags": settings.valsea_enable_tags,
        },
    )
    resp.raise_for_status()
    return resp.json()


async def _format(client: httpx.AsyncClient, base: str, transcript: str, output_type: str) -> Any:
    resp = await client.post(
        f"{base}/v1/formatting",
        json={
            "model": "valsea-format",
            "transcript": transcript,
            "output_type": output_type,
            "response_format": "json",
        },
    )
    resp.raise_for_status()
    return resp.json()


async def _translate(client: httpx.AsyncClient, base: str, text: str, target: str) -> str:
    resp = await client.post(
        f"{base}/v1/translations",
        json={
            "model": "valsea-translate",
            "text": text,
            "source": "auto",
            "target": (target or "english").strip().lower(),
            "response_format": "json",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("translated_text") or ""


def _extract_semantic_tags(payload: Any) -> list[dict[str, Any]]:
    """Chuẩn hóa semantic tags từ nhiều shape response khác nhau."""
    if not isinstance(payload, dict):
        return []
    raw = payload.get("semantic_tags") or payload.get("annotations") or []
    if isinstance(raw, dict):
        raw = raw.get("semantic_tags") or raw.get("items") or raw.get("tags") or []
    if not isinstance(raw, list):
        return []

    tags: list[dict[str, Any]] = []
    for item in raw[:24]:
        if isinstance(item, dict):
            phrase = item.get("phrase") or item.get("text") or item.get("value") or item.get("tag") or ""
            tag = item.get("tag") or item.get("type") or item.get("category") or "semantic"
            meaning = item.get("meaning") or item.get("description") or item.get("label") or ""
            tags.append({"tag": str(tag), "phrase": str(phrase), "meaning": str(meaning)})
        else:
            tags.append({"tag": "semantic", "phrase": str(item), "meaning": ""})
    return tags


def _extract_lines(payload: Any) -> list[str]:
    """Rút nội dung formatting thành list ngắn để UI render ổn định."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return [str(x).strip() for x in payload if str(x).strip()][:12]
    if isinstance(payload, dict):
        for key in (
            "formatted_text",
            "text",
            "output",
            "result",
            "content",
            "action_items",
            "key_quotes",
            "meeting_minutes",
            "notes",
        ):
            if key in payload:
                return _extract_lines(payload[key])
        return [json.dumps(payload, ensure_ascii=False)[:800]]

    text = str(payload).strip()
    if not text:
        return []
    lines = [ln.strip(" -•\t") for ln in re.split(r"\n+|(?<=\.)\s+(?=[A-ZÀ-Ỹ0-9])", text)]
    return [ln for ln in lines if len(ln) > 3][:12]


def _fallback_enrichment(transcript: str, summary: str) -> dict[str, Any]:
    """Fallback không tốn credit, dùng khi chưa có key hoặc enrichment bị tắt."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript.strip()) if len(s.strip()) > 20]
    notes = sentences[:5] or [summary[:240]]
    actions = [
        "Đọc lại tóm tắt và đánh dấu 3 khái niệm chưa chắc.",
        "Ôn bộ thẻ bằng Again / Hard / Good / Easy.",
        "Làm lại quiz sau 24 giờ cho các câu sai.",
    ]
    quotes = [s[:180] + ("…" if len(s) > 180 else "") for s in sentences[:3]]
    return {
        "clarified_transcript": transcript,
        "semantic_tags": [],
        "formatted_notes": FormattedNotes(
            lecture_notes=notes,
            action_items=actions,
            key_quotes=quotes,
        ),
        "bilingual_summary": {"vietnamese": summary},
        "enrichment_warnings": [],
    }
