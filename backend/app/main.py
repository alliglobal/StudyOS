# File khởi tạo FastAPI: đăng ký CORS, route upload / text, gọi pipeline xử lý bài giảng.
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import ProcessResponse, TranscriptIn
from app.services.live_rtt_service import live_transcription_session
from app.services.pipeline import process_transcript, run_lesson_pipeline

# Tạo instance ứng dụng FastAPI với metadata cho OpenAPI / docs.
app = FastAPI(
    title="Post-Lesson AI Pipeline",
    description="Audio → ASR → chunk → summarize → knowledge graph → quiz (demo VALSEA hackathon)",
    version="0.1.0",
)

# Tách chuỗi CORS theo dấu phẩy thành list URL được phép.
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
# Thêm middleware CORS để trình duyệt từ React gọi được API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    # Endpoint kiểm tra nhanh server sống (load balancer / dev).
    return {"status": "ok"}


@app.post("/api/process-audio", response_model=ProcessResponse)
async def process_audio(file: UploadFile = File(...)):
    """
    Nhận file audio bài giảng (multipart field name: file).
    Trả JSON: summary, flashcards, graph, 3 điểm ôn, 5 câu quiz.
    """
    # Gọi pipeline bất đồng bộ: đọc file, ASR, suy luận phía server.
    result = await run_lesson_pipeline(file)
    # FastAPI serialize ProcessResponse thành JSON cho client.
    return result


@app.post("/api/process-text", response_model=ProcessResponse)
async def process_text(body: TranscriptIn):
    """
    Nhận transcript dạng JSON (đã có ASR ở nơi khác hoặc dán thử nghiệm).
    Bỏ qua bước ASR; chạy chunk → tóm tắt → đồ thị → quiz giống upload audio.
    """
    # Lấy chuỗi và loại bỏ khoảng trắng hai đầu.
    raw = body.transcript.strip()
    # Không cho phép transcript rỗng (trả 400 rõ ràng cho client).
    if not raw:
        raise HTTPException(status_code=400, detail="transcript không được rỗng")
    # Gọi pipeline bất đồng bộ trên transcript đã chuẩn hóa.
    return await process_transcript(raw)


@app.websocket("/ws/live-transcribe")
async def live_transcribe(websocket: WebSocket):
    """
    WebSocket realtime:
    frontend gửi PCM16 base64 → backend proxy VALSEA RTT → trả partial/final transcript.
    Khi stop, backend tự tạo full study pack (flashcards/quiz/notes) từ transcript live.
    """
    await live_transcription_session(websocket)
