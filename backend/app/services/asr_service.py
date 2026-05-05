# Dịch vụ ASR: VALSEA thật (OpenAI-compatible) hoặc transcript mẫu khi không có API key.
import json
import logging

import httpx
from fastapi import HTTPException, UploadFile

from app.config import settings

logger = logging.getLogger(__name__)

# Transcript mẫu khi không cấu hình API key (demo offline).
MOCK_LECTURE_TRANSCRIPT = """
Hôm nay chúng ta học về machine learning cơ bản. Đầu tiên supervised learning là học có giám sát,
tức là chúng ta có label cho từng mẫu dữ liệu. Ví dụ classification phân loại email spam hay không spam.
Tiếp theo unsupervised learning không có nhãn, ví dụ clustering để gom nhóm khách hàng.
Overfitting là hiện tượng model học thuộc training data quá kỹ nên generalize kém trên test set.
Chúng ta cần regularization và cross validation để giảm overfitting. Cuối cùng gradient descent
là thuật toán tối ưu hàm loss bằng cách cập nhật weights theo hướng âm gradient.
"""

# Model bắt buộc theo https://valsea.ai/llms.txt
VALSEA_TRANSCRIBE_MODEL = "valsea-transcribe"


async def transcribe_audio(upload: UploadFile) -> str:
    """
    Đọc file upload và trả về transcript.
    Có VALSEA_API_KEY → POST https://api.valsea.ai/v1/audio/transcriptions (multipart + model + language).
    Không có key → transcript mẫu.
    """
    raw = await upload.read()
    filename = upload.filename or "lecture.wav"
    content_type = upload.content_type or "application/octet-stream"

    if not (settings.valsea_api_key or "").strip():
        return MOCK_LECTURE_TRANSCRIPT.strip()

    base = settings.valsea_base_resolved()
    url = f"{base}/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {settings.valsea_api_key.strip()}",
        "Accept": "application/json",
    }

    # Multipart: file + các field bắt buộc theo tài liệu VALSEA.
    files = {"file": (filename, raw, content_type)}
    data = {
        "model": VALSEA_TRANSCRIBE_MODEL,
        "language": (settings.valsea_language or "vietnamese").strip().lower(),
        "response_format": (settings.valsea_response_format or "json").strip().lower(),
        "enable_correction": str(settings.valsea_enable_correction).lower(),
        "enable_tags": str(settings.valsea_enable_tags).lower(),
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, headers=headers, files=files, data=data)
    except httpx.RequestError as e:
        logger.exception("VALSEA request failed")
        raise HTTPException(status_code=502, detail=f"Không kết nối được VALSEA: {e!s}") from e

    if resp.status_code >= 400:
        detail = _safe_error_body(resp)
        logger.warning("VALSEA ASR error %s: %s", resp.status_code, detail[:300])
        raise HTTPException(status_code=resp.status_code, detail=detail)

    try:
        payload = resp.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="VALSEA trả về không phải JSON hợp lệ.",
        ) from None

    text = (
        (payload.get("text") or "").strip()
        or (payload.get("transcript") or "").strip()
        or (payload.get("raw_transcript") or "").strip()
    )
    if not text:
        raise HTTPException(
            status_code=502,
            detail="VALSEA trả về thành công nhưng không có trường text/transcript.",
        )
    return text


def _safe_error_body(resp: httpx.Response) -> str:
    """Chuỗi lỗi ngắn gọn cho client (401/402/413…)."""
    try:
        j = resp.json()
        if isinstance(j, dict):
            msg = j.get("message") or j.get("error") or j.get("detail")
            if isinstance(msg, dict):
                msg = json.dumps(msg, ensure_ascii=False)
            if msg:
                return str(msg)[:800]
    except json.JSONDecodeError:
        pass
    t = (resp.text or "").strip()
    return t[:800] if t else f"HTTP {resp.status_code}"
