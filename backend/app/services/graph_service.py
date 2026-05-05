# Xây đồ thị tri thức đơn giản giữa các chunk (cạnh = từ vựng trùng).
import re
from collections import Counter

from app.schemas import GraphEdge, GraphNode


def _token_set(text: str) -> set[str]:
    """Chuẩn hóa text thành tập token chữ thường (dùng so trùng giữa hai đoạn)."""
    # Regex tương tự summarize_service cho tiếng Việt + ASCII.
    lower = text.lower()
    tokens = re.findall(r"[a-z0-9àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+", lower)
    # Bỏ từ quá ngắn.
    return {t for t in tokens if len(t) >= 3}


def jaccard(a: set[str], b: set[str]) -> float:
    """Độ tương đồng Jaccard giữa hai tập từ: |giao| / |hợp|."""
    # Nếu cả hai rỗng thì coi như không liên quan.
    if not a and not b:
        return 0.0
    # Phần giao.
    inter = len(a & b)
    # Phần hợp.
    union = len(a | b)
    # Tránh chia cho 0.
    if union == 0:
        return 0.0
    # Trả về tỉ lệ 0–1.
    return inter / union


def build_knowledge_graph(
    chunks: list[str],
    chunk_summaries: list[str],
    edge_threshold: float = 0.08,
) -> tuple[list[GraphNode], list[GraphEdge]]:
    """
    Tạo nodes (mỗi chunk một nút) và edges nếu Jaccard token > ngưỡng.
    Trả về (nodes, edges).
    """
    # Danh sách nút.
    nodes: list[GraphNode] = []
    # Tiền tính token set cho mỗi chunk (dùng lại cho cạnh).
    token_sets = [_token_set(c) for c in chunks]

    # Tạo nút cho từng chunk.
    for i, summary in enumerate(chunk_summaries):
        # ID cố định dạng c0, c1, ...
        nid = f"c{i}"
        # Nhãn nút: tóm tắt rút ngắn (120 ký tự).
        label = summary[:120] + ("…" if len(summary) > 120 else "")
        # Thêm GraphNode vào list.
        nodes.append(GraphNode(id=nid, label=label, chunk_index=i))

    # Danh sách cạnh.
    edges: list[GraphEdge] = []
    # So từng cặp i < j.
    n = len(chunks)
    for i in range(n):
        for j in range(i + 1, n):
            # Tính độ tương đồng.
            w = jaccard(token_sets[i], token_sets[j])
            # Chỉ thêm cạnh nếu vượt ngưỡng.
            if w >= edge_threshold:
                edges.append(GraphEdge(source=f"c{i}", target=f"c{j}", weight=round(w, 4)))

    return nodes, edges


def weak_chunk_indices(
    num_chunks: int,
    edges: list[GraphEdge],
    top_k: int = 3,
) -> list[int]:
    """
    Xác định các đoạn “yếu” / cần ôn: bậc (degree) thấp trong đồ thị = ít liên kết với phần còn lại.
    """
    # Nếu không có chunk thì trả rỗng.
    if num_chunks <= 0:
        return []
    # Đếm số cạnh nối tới mỗi chỉ số chunk (vô hướng: mỗi cạnh tăng degree cho cả i và j).
    degree: Counter[int] = Counter()
    # Duyệt từng cạnh.
    for e in edges:
        # Parse id "c0" -> 0
        si = int(e.source.removeprefix("c"))
        sj = int(e.target.removeprefix("c"))
        degree[si] += 1
        degree[sj] += 1

    # Mọi chunk từ 0..n-1 kể cả degree 0.
    scores = [(i, degree.get(i, 0)) for i in range(num_chunks)]
    # Sắp xếp theo degree tăng dần (ít liên kết nhất trước).
    scores.sort(key=lambda x: x[1])
    # Lấy top_k chỉ số đầu.
    return [i for i, _ in scores[: min(top_k, num_chunks)]]


def review_points_from_weak(
    weak_indices: list[int],
    chunk_summaries: list[str],
    chunks: list[str],
) -> list[str]:
    """
    Chuyển chỉ số đoạn yếu thành 3 mục ôn tập có cấu trúc (mục tiêu + hành động + trích dẫn).
    """
    out: list[str] = []
    labels = ("Ưu tiên cao", "Ưu tiên trung bình", "Ưu tiên bổ sung")

    for rank, idx in enumerate(weak_indices[:3], start=1):
        label = labels[rank - 1] if rank <= len(labels) else f"Mức {rank}"
        if 0 <= idx < len(chunk_summaries):
            snippet = chunk_summaries[idx][:140].rstrip()
            excerpt = ""
            if 0 <= idx < len(chunks):
                excerpt = chunks[idx].strip().replace("\n", " ")
                if len(excerpt) > 120:
                    excerpt = excerpt[:119] + "…"
            if excerpt:
                out.append(
                    f"{label} · Phần {idx + 1}: ít liên kết với các đoạn khác trong đồ thị tri thức. "
                    f"Mục tiêu: nói lại ý chính không nhìn giáo trình. "
                    f"Neo ngữ cảnh: “{excerpt}” — gợi ý: viết 3 bullet tóm tắt lại phần này."
                )
            else:
                out.append(
                    f"{label} · Phần {idx + 1}: {snippet}… — "
                    f"làm lại 2 câu hỏi tự đặt (active recall) rồi đối chiếu với tóm tắt đoạn."
                )
        else:
            out.append(f"{label}: ôn lại phần {idx + 1} theo checklist trong study guide.")

    while len(out) < 3:
        out.append(
            "Hoàn thành toàn bộ quiz; mỗi câu sai lập một thẻ bổ sung (mặt trước: lỗi hay mắc, mặt sau: sửa lý)."
        )
    return out[:3]
