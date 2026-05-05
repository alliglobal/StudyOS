# Sinh 5 câu quiz trắc nghiệm, ưu tiên gắn với các đoạn được đánh dấu yếu.
import re
import uuid
from random import shuffle

from app.schemas import QuizQuestion
from app.services.summarize_service import _keywords


def _sentences(text: str) -> list[str]:
    """Tách văn bản thành danh sách câu ngắn."""
    # Split giữ nguyên logic đơn giản.
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    # Lọc câu đủ dài.
    return [p.strip() for p in parts if len(p.strip()) > 20]


def _distractors_from_other_chunks(chunks: list[str], avoid_idx: int, need: int) -> list[str]:
    """Lấy các cụm từ từ chunk khác làm phương án nhiễu."""
    # Pool chứa các chuỗi ngắn làm đáp án sai.
    pool: list[str] = []
    # Duyệt từng chunk không phải avoid_idx.
    for i, ch in enumerate(chunks):
        if i == avoid_idx:
            continue
        # Lấy keyword làm distracto ngắn gọn.
        for kw in _keywords(ch, top_n=3):
            pool.append(kw.replace("_", " "))
    # Xáo trộn để quiz không lặp pattern.
    shuffle(pool)
    # Trả về đủ need phần tử (unique).
    out: list[str] = []
    for p in pool:
        if p not in out:
            out.append(p)
        if len(out) >= need:
            break
    # Nếu thiếu thì pad bằng chuỗi chung.
    while len(out) < need:
        out.append("Không đề cập trong bài")
    return out[:need]


def build_quiz(
    chunks: list[str],
    weak_indices: list[int],
    num_questions: int = 5,
) -> list[QuizQuestion]:
    """
    Tạo num_questions câu hỏi: phần lớn lấy từ weak_indices (cá nhân hóa 'bạn yếu phần này').
    Mỗi câu 4 lựa chọn, một đúng.
    """
    # Nếu không có chunk thì trả rỗng.
    if not chunks:
        return []

    # Thứ tự ưu tiên: các chunk yếu trước, sau đó các chỉ số còn lại.
    order: list[int] = []
    # Thêm weak trước (không trùng).
    seen: set[int] = set()
    for wi in weak_indices:
        if 0 <= wi < len(chunks) and wi not in seen:
            order.append(wi)
            seen.add(wi)
    # Thêm các index còn lại.
    for i in range(len(chunks)):
        if i not in seen:
            order.append(i)
            seen.add(i)

    # Danh sách câu hỏi đầu ra.
    questions: list[QuizQuestion] = []

    # Duyệt cho đủ num_questions.
    for q in range(num_questions):
        # Chọn chunk theo vòng lặp order.
        idx = order[q % len(order)]
        chunk = chunks[idx]
        # Lấy câu đầu tiên đủ dài làm “stem” câu hỏi.
        sents = _sentences(chunk)
        stem = sents[0] if sents else chunk[:120]
        # Đáp án đúng: tóm tắt keyword chính.
        kws = _keywords(chunk, top_n=1)
        correct = kws[0] if kws else stem[:40]
        # Tạo câu hỏi dạng hiểu ý chính.
        question_text = f"Theo bài giảng, ý chính liên quan tới đoạn sau là gì?\n“{stem[:220]}…”"
        # Ba phương án sai.
        wrongs = _distractors_from_other_chunks(chunks, idx, 6)
        # Loại phương án trùng nội dung với đáp án đúng (so sánh không phân biệt hoa thường).
        wrongs = [w for w in wrongs if w.lower() != correct.lower()]
        # Đảm bảo đủ 3 phương án sai (pad nếu thiếu).
        pad = ["Khái niệm khác trong bài", "Ý không được nhắc trong đoạn", "Thuật ngữ nền tảng khác"]
        for p in pad:
            if len(wrongs) >= 3:
                break
            if p.lower() != correct.lower() and p not in wrongs:
                wrongs.append(p)
        wrongs = wrongs[:3]
        # Gom 4 lựa chọn.
        choices = [correct] + wrongs
        # Xáo vị trí đáp án đúng.
        shuffle(choices)
        # Tìm chỉ số đúng sau shuffle.
        correct_index = choices.index(correct)
        # UUID ngắn cho id câu hỏi.
        qid = str(uuid.uuid4())[:8]
        # Append QuizQuestion.
        questions.append(
            QuizQuestion(
                id=qid,
                question=question_text,
                choices=choices,
                correct_index=correct_index,
                related_chunk_index=idx,
            )
        )

    return questions[:num_questions]
