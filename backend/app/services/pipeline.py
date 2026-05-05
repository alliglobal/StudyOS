# Ghép pipeline: ASR → chunk → summarize → graph → weak → quiz.
from fastapi import UploadFile

from app.schemas import Flashcard, ProcessResponse
from app.services import (
    asr_service,
    chunk_service,
    graph_service,
    quiz_service,
    summarize_service,
    valsea_nlp_service,
)


async def process_transcript(transcript: str) -> ProcessResponse:
    """
    Chạy toàn bộ pipeline từ một chuỗi transcript đã có (không đọc file audio).
    Dùng chung cho /api/process-text và sau bước ASR của /api/process-audio.
    """
    # Chuẩn hóa khoảng trắng đầu cuối.
    text = transcript.strip()
    # Bước chunk: chia văn bản thành các đoạn.
    chunks = chunk_service.split_into_chunks(text)
    # Fallback một chunk nếu rỗng sau split (trường hợp edge).
    if not chunks:
        chunks = [text] if text else ["(Không có nội dung)"]

    # Tóm tắt từng chunk.
    chunk_summaries = [summarize_service.summarize_chunk(c) for c in chunks]
    # Tóm tắt toàn bài (đoạn mở + mạch ý).
    full_summary = summarize_service.summarize_full(chunks, chunk_summaries)
    # Thẻ ôn chuyên nghiệp (dict → Flashcard).
    flash_dicts = summarize_service.build_professional_flashcards(chunks)
    flashcards = [Flashcard(**d) for d in flash_dicts]

    # Đồ thị tri thức + đoạn yếu + điểm ôn + quiz.
    nodes, edges = graph_service.build_knowledge_graph(chunks, chunk_summaries)
    weak = graph_service.weak_chunk_indices(len(chunks), edges, top_k=3)
    review = graph_service.review_points_from_weak(weak, chunk_summaries, chunks)
    # Checklist ôn tập (ưu tiên phần yếu + spaced repetition).
    study_guide = summarize_service.build_study_guide(chunks, chunk_summaries, weak)
    quiz = quiz_service.build_quiz(chunks, weak, num_questions=5)
    # VALSEA text enrichment: clarify, annotate, format notes, translate summary.
    enrichment = await valsea_nlp_service.enrich_transcript(text, full_summary)

    return ProcessResponse(
        transcript=text,
        clarified_transcript=enrichment["clarified_transcript"],
        summary=full_summary,
        bilingual_summary=enrichment["bilingual_summary"],
        formatted_notes=enrichment["formatted_notes"],
        semantic_tags=enrichment["semantic_tags"],
        enrichment_warnings=enrichment["enrichment_warnings"],
        study_guide=study_guide,
        flashcards=flashcards,
        graph_nodes=nodes,
        graph_edges=edges,
        weak_chunk_indices=weak,
        review_points=review,
        quiz=quiz,
    )


async def run_lesson_pipeline(upload: UploadFile) -> ProcessResponse:
    """
    Luồng đầy đủ: file audio → ASR → cùng pipeline với process_transcript.
    """
    # Bước ASR (VALSEA hoặc transcript mẫu khi không cấu hình API).
    transcript = await asr_service.transcribe_audio(upload)
    # Phần còn lại giống nhập text thủ công.
    return await process_transcript(transcript)
