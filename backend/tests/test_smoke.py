# Smoke test API: không cần chạy server, dùng TestClient của Starlette/FastAPI.
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    # TestClient bọc ASGI app để gọi HTTP trong process.
    return TestClient(app)


def test_health(client):
    # GET /health phải trả 200 và JSON status ok.
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_process_text_returns_quiz_and_reviews(client, monkeypatch):
    # Tắt enrichment thật để smoke test không tốn credit và không phụ thuộc mạng.
    from app.config import settings as real_settings
    from app.services import valsea_nlp_service

    fake = real_settings.model_copy(
        update={"valsea_api_key": "", "valsea_enable_enrichment": False}
    )
    monkeypatch.setattr(valsea_nlp_service, "settings", fake)
    # Gửi transcript ngắn đủ chunk để sinh quiz.
    payload = {
        "transcript": "Phần một nói về neural network. Phần hai nói về backpropagation và gradient. "
        "Phần ba là regularization. Phần bốn là deployment trên cloud."
    }
    r = client.post("/api/process-text", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert len(data["quiz"]) == 5
    assert len(data["review_points"]) == 3
    assert "summary" in data and data["summary"]
    assert "study_guide" in data and len(data["study_guide"]) >= 3
    assert data["flashcards"] and all("id" in fc and "ease_factor" in fc for fc in data["flashcards"])


def test_process_audio_uses_mock_transcript(client, monkeypatch):
    # Copy settings không key — patch module asr (import riêng nên phải patch đúng chỗ).
    from app.config import settings as real_settings
    from app.services import asr_service, valsea_nlp_service

    fake = real_settings.model_copy(update={"valsea_api_key": ""})
    monkeypatch.setattr(asr_service, "settings", fake)
    monkeypatch.setattr(valsea_nlp_service, "settings", fake)
    # Upload bytes giả; không có VALSEA key → transcript mẫu → vẫn 200.
    files = {"file": ("x.wav", BytesIO(b"fake"), "audio/wav")}
    r = client.post("/api/process-audio", files=files)
    assert r.status_code == 200
    data = r.json()
    assert len(data["quiz"]) == 5
    assert "machine learning" in data["transcript"].lower() or "học" in data["transcript"].lower()
