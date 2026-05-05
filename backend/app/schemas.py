# Các mô hình Pydantic: định nghĩa cấu trúc JSON request/response cho FastAPI.
from typing import Any, Literal

from pydantic import BaseModel, Field


class Flashcard(BaseModel):
    # Thẻ ôn tập có cấu trúc (gần với thẻ Anki: mặt trước/sau + meta + SM-2 khởi tạo).
    id: str = Field(..., description="ID ổn định để lưu SM-2 phía client")
    front: str = Field(..., description="Mặt trước: câu hỏi rõ ràng")
    back: str = Field(..., description="Mặt sau: đáp án có bullet, dễ quét mắt")
    topic_tag: str = Field(default="", description="Nhãn chủ đề (từ khóa nổi bật)")
    source_excerpt: str = Field(default="", description="Trích một câu từ bài để neo ngữ cảnh")
    card_kind: Literal["definition", "connection", "exam_style"] = Field(
        default="definition",
        description="Loại thẻ: định nghĩa / liên hệ / tự kiểm tra",
    )
    # Giá trị khởi tạo SM-2 (Anki dùng EF mặc định ~2.5).
    ease_factor: float = Field(default=2.5, ge=1.3, description="Hệ số dễ (ease factor)")
    interval_days: float = Field(default=0.0, ge=0, description="Khoảng cách hiện tại (ngày)")
    repetitions: int = Field(default=0, ge=0, description="Số lần trả lời đạt (chuỗi ôn)")


class GraphNode(BaseModel):
    # Một nút trong đồ thị tri thức (thường là khái niệm / đoạn bài).
    id: str = Field(..., description="ID duy nhất của nút")
    label: str = Field(..., description="Nhãn hiển thị (tóm tắt ngắn)")
    chunk_index: int = Field(..., description="Chỉ số đoạn văn gốc")


class GraphEdge(BaseModel):
    # Cạnh nối hai nút khi hai đoạn có liên quan từ vựng.
    source: str = Field(..., description="ID nút nguồn")
    target: str = Field(..., description="ID nút đích")
    weight: float = Field(..., description="Độ liên quan 0–1")


class QuizQuestion(BaseModel):
    # Một câu hỏi trắc nghiệm sinh ra từ nội dung bài.
    id: str = Field(..., description="ID câu hỏi")
    question: str = Field(..., description="Nội dung câu hỏi")
    choices: list[str] = Field(..., description="Các lựa chọn A,B,C,...")
    correct_index: int = Field(..., description="Chỉ số đáp án đúng (0-based)")
    related_chunk_index: int = Field(..., description="Đoạn nguồn để truy vết")


class FormattedNotes(BaseModel):
    # Gói ghi chú được VALSEA formatting hoặc fallback heuristic tạo ra.
    lecture_notes: list[str] = Field(default_factory=list, description="Ghi chú bài giảng có cấu trúc")
    action_items: list[str] = Field(default_factory=list, description="Việc cần làm sau tiết học")
    key_quotes: list[str] = Field(default_factory=list, description="Câu trích dẫn / ý đáng nhớ")


class TranscriptIn(BaseModel):
    # Body JSON cho endpoint nhập sẵn transcript (bỏ qua bước ASR).
    transcript: str = Field(..., min_length=1, description="Toàn bộ văn bản bài giảng sau ghi âm/ghép ASR")


class ProcessResponse(BaseModel):
    # Phản hồi đầy đủ sau pipeline: ASR → chunk → tóm tắt → đồ thị → quiz.
    transcript: str = Field(..., description="Toàn bộ văn bản sau ASR")
    clarified_transcript: str = Field(
        default="",
        description="Transcript đã được VALSEA Clarify làm sạch (nếu bật enrichment)",
    )
    summary: str = Field(..., description="Tóm tắt toàn bài (đoạn mở đầu + ý chính)")
    bilingual_summary: dict[str, str] = Field(
        default_factory=dict,
        description="Tóm tắt song ngữ, ví dụ {'vietnamese': '...', 'english': '...'}",
    )
    formatted_notes: FormattedNotes = Field(
        default_factory=FormattedNotes,
        description="Lecture notes, action items, key quotes",
    )
    semantic_tags: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Semantic tags từ VALSEA Annotate",
    )
    enrichment_warnings: list[str] = Field(
        default_factory=list,
        description="Cảnh báo nếu bước enrichment phụ thất bại",
    )
    study_guide: list[str] = Field(
        ...,
        description="Checklist ôn tập chuyên nghiệp (bullet có hành động)",
    )
    flashcards: list[Flashcard] = Field(..., description="Thẻ ôn tập có meta + SM-2 khởi tạo")
    graph_nodes: list[GraphNode] = Field(..., description="Nút đồ thị tri thức")
    graph_edges: list[GraphEdge] = Field(..., description="Cạnh đồ thị")
    weak_chunk_indices: list[int] = Field(
        ...,
        description="Chỉ số các đoạn cần ôn (ít liên kết trong đồ thị)",
    )
    review_points: list[str] = Field(
        ...,
        description="Ba điểm cần ôn lại (tiếng Việt, dễ đọc)",
    )
    quiz: list[QuizQuestion] = Field(..., description="Năm câu quiz cá nhân hóa")
