# Chia transcript thành các đoạn (chunk) để tóm tắt và xây đồ thị theo từng phần.
import re


def split_into_chunks(text: str, max_chars: int = 450) -> list[str]:
    """
    Chia văn bản thành list các đoạn ngắn.
    Ưu tiên tách theo câu (dấu chấm), sau đó ghép câu cho đến max_chars.
    """
    # Chuẩn hóa khoảng trắng: thay mọi whitespace liên tiếp bằng một dấu cách.
    normalized = re.sub(r"\s+", " ", text).strip()
    # Nếu rỗng thì trả list rỗng (caller xử lý).
    if not normalized:
        return []

    # Tách theo dấu câu đơn giản (. ! ?) giữ lại nội dung câu.
    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    # Danh sách chunk đầu ra.
    chunks: list[str] = []
    # Buffer đang ghép các câu cho một chunk.
    buf: list[str] = []
    # Độ dài ký tự hiện tại của buffer.
    cur_len = 0

    # Duyệt từng câu đã tách.
    for sent in sentences:
        # Bỏ qua câu rỗng sau split.
        if not sent:
            continue
        # Nếu thêm câu này vượt max_chars và buffer đã có nội dung thì flush buffer.
        if buf and cur_len + len(sent) + 1 > max_chars:
            # Ghép các câu trong buffer thành một chuỗi chunk.
            chunks.append(" ".join(buf).strip())
            # Xóa buffer và reset độ dài.
            buf, cur_len = [], 0
        # Thêm câu vào buffer.
        buf.append(sent)
        # Cập nhật độ dài (cộng thêm 1 cho khoảng cách giữa câu).
        cur_len += len(sent) + 1

    # Flush phần còn lại sau vòng lặp.
    if buf:
        chunks.append(" ".join(buf).strip())

    # Nếu vì lý do nào đó không có chunk (ví dụ một câu cực dài), cắt cứng theo max_chars.
    if not chunks and normalized:
        return [normalized[i : i + max_chars] for i in range(0, len(normalized), max_chars)]
    return chunks
