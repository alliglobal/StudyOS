# Tóm tắt từng chunk, tóm tắt toàn bài, thẻ ôn chuyên nghiệp, study guide (không cần LLM).
import re
import uuid
from collections import Counter


def _keywords(text: str, top_n: int = 5) -> list[str]:
    """Trích các từ có ý nghĩa (bỏ stopword tiếng Việt/Anh đơn giản)."""
    lower = text.lower()
    tokens = re.findall(r"[a-z0-9àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+", lower)
    stop = {
        "là", "và", "của", "cho", "với", "để", "một", "các", "trên", "trong", "từ", "the", "a", "an",
        "is", "are", "to", "of", "and", "or", "we", "you", "it", "by", "as", "at", "on", "in", "for",
        "ta", "còn", "này", "đó", "khi", "thì", "được", "sẽ", "đã", "như", "vì", "theo",
    }
    filtered = [t for t in tokens if len(t) >= 3 and t not in stop]
    cnt = Counter(filtered)
    return [w for w, _ in cnt.most_common(top_n)]


def _sentences(text: str) -> list[str]:
    """Tách văn bản thành các câu đủ dài."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 12]


def _excerpt(chunk: str, max_len: int = 160) -> str:
    """Một câu trích dẫn ngắn làm neo ngữ cảnh cho thẻ."""
    sents = _sentences(chunk)
    if sents:
        s = sents[0]
        return s if len(s) <= max_len else s[: max_len - 1].rstrip() + "…"
    t = chunk.strip()
    return t if len(t) <= max_len else t[: max_len - 1].rstrip() + "…"


def summarize_chunk(chunk: str) -> str:
    """Tóm tắt một đoạn: câu dẫn + từ khóa."""
    lead = chunk[:200].strip()
    if len(chunk) > 200:
        lead = lead.rstrip() + "…"
    kws = _keywords(chunk, top_n=4)
    kw_str = ", ".join(kws) if kws else ""
    if kw_str:
        return f"{lead} — Khái niệm chính: {kw_str}."
    return lead


def summarize_full(chunks: list[str], chunk_summaries: list[str]) -> str:
    """Tóm tắt toàn bài: tiêu đề + đoạn văn mạch lạc."""
    if not chunk_summaries:
        return "Không có nội dung để tóm tắt."
    n = len(chunks)
    lead = (
        f"Sau tiết học, bạn cần nắm {n} khối ý chính. "
        f"Dưới đây là đường đi tư duy nhanh — dùng kèm checklist ôn tập và bộ thẻ."
    )
    body_parts = []
    for i, sm in enumerate(chunk_summaries[: min(5, n)], start=1):
        body_parts.append(f"({i}) {sm[:220]}{'…' if len(sm) > 220 else ''}")
    body = " ".join(body_parts)
    if len(body) > 900:
        body = body[:900].rstrip() + "…"
    return f"{lead}\n\n{body}"


def build_study_guide(
    chunks: list[str],
    chunk_summaries: list[str],
    weak_indices: list[int],
) -> list[str]:
    """
    Checklist ôn tập 'chuyên nghiệp': hành động cụ thể, ưu tiên phần yếu, gợi ý spaced repetition.
    """
    lines: list[str] = []
    lines.append("Đọc lướt toàn bộ tóm tắt một lần, đánh dấu chỗ chưa hiểu (60–90 giây).")
    lines.append("Làm quiz: mỗi câu sai → ghi 1 dòng 'sai vì sao' vào sổ tay (active recall).")
    for rank, wi in enumerate(weak_indices[:3], start=1):
        if 0 <= wi < len(chunks):
            ex = _excerpt(chunks[wi], 100)
            lines.append(f"Ưu tiên ôn phần {wi + 1} (mức {rank}): đọc trích \"{ex}\" rồi tự kể lại bằng miệng.")
        else:
            lines.append(f"Ưu tiên ôn phần {wi + 1}: lặp lại tóm tắt đoạn tương ứng.")
    lines.append("Chạy bộ thẻ: Again/Hard/Good/Easy — lịch ôn theo SM-2 (cùng họ với thuật toán cốt lõi Anki).")
    lines.append("Sau 24 giờ: ôn lại chỉ các thẻ bạn đã bấm Again/Hard (spaced repetition).")
    if len(chunk_summaries) > 3:
        lines.append("Cuối tuần: vẽ sơ đồ mini nối các khái niệm giữa 3 phần mạnh nhất trong bài.")
    return lines[:10]


def build_professional_flashcards(chunks: list[str], max_cards: int = 8) -> list[dict]:
    """
    Sinh thẻ chất lượng cao: câu hỏi rõ ràng, đáp án có cấu trúc, trích dẫn, meta SM-2 ban đầu.
    Trả về list dict để pipeline bọc Flashcard.
    """
    out: list[dict] = []
    kinds = ("definition", "connection", "exam_style")

    for i, ch in enumerate(chunks[:max_cards]):
        cid = uuid.uuid4().hex[:12]
        kws = _keywords(ch, top_n=4)
        term = kws[0] if kws else f"ý chính phần {i + 1}"
        topic_tag = " · ".join(kws[:2]) if kws else f"Phần {i + 1}"
        excerpt = _excerpt(ch, 140)
        sents = _sentences(ch)
        core = " ".join(sents[:2]) if sents else ch[:280].strip()

        kind = kinds[i % len(kinds)]
        if kind == "definition":
            front = f"Khái niệm trọng tâm “{term}” trong phần {i + 1} được hiểu như thế nào?"
            back = (
                f"Trả lời ngắn:\n• {core[:320]}{'…' if len(core) > 320 else ''}\n\n"
                f"Ghi nhớ nhanh:\n• Từ khóa: {', '.join(kws[:3]) if kws else '—'}\n\n"
                f"Kiểm tra: bạn có diễn giải lại được ý này trong ≤20 giây không?"
            )
        elif kind == "connection":
            other = kws[1] if len(kws) > 1 else "phần trước"
            front = f"“{term}” liên hệ thế nào với “{other}” trong luồng bài giảng?"
            back = (
                f"Mối liên hệ:\n• Cùng xuất hiện trong ngữ cảnh: {topic_tag}\n• "
                f"Ý nối: {core[:280]}{'…' if len(core) > 280 else ''}\n\n"
                f"Mẹo ôn: vẽ một mũi tên giữa hai khái niệm và ghi nhãn quan hệ (nguyên nhân / ví dụ / đối lập)."
            )
        else:
            front = f"Tự kiểm tra: nếu thi vấn đáp về phần {i + 1}, câu hỏi khó nhất có thể là gì?"
            back = (
                f"Gợi ý câu hỏi:\n• “{term}” được định nghĩa/ứng dụng ra sao trong đoạn này?\n\n"
                f"Đáp án khung:\n• {core[:300]}{'…' if len(core) > 300 else ''}"
            )

        out.append(
            {
                "id": cid,
                "front": front.strip(),
                "back": back.strip(),
                "topic_tag": topic_tag,
                "source_excerpt": excerpt,
                "card_kind": kind,
                "ease_factor": 2.5,
                "interval_days": 0.0,
                "repetitions": 0,
            }
        )

    return out


# Giữ tên cũ cho import nội bộ nếu cần — ủy quyền sang bản chuyên nghiệp.
def build_flashcards(chunks: list[str], max_cards: int = 8) -> list[dict]:
    return build_professional_flashcards(chunks, max_cards=max_cards)
