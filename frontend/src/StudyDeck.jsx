/**
 * Bộ thẻ ôn tập kiểu Anki: lật thẻ + 4 mức đánh giá (Again / Hard / Good / Easy).
 * Trạng thái SM-2 lưu localStorage theo sessionKey để giữ lịch ôn giữa các lần mở trang.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { formatIntervalVi, previewIntervalVi, sm2Update } from "./sm2.js";

const STORAGE_PREFIX = "valsea-sm2-";

function loadStates(sessionKey) {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + sessionKey);
    if (!raw) return {};
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function saveStates(sessionKey, states) {
  try {
    localStorage.setItem(STORAGE_PREFIX + sessionKey, JSON.stringify(states));
  } catch {
    /* ignore quota */
  }
}

export default function StudyDeck({ sessionKey, flashcards }) {
  const list = flashcards ?? [];
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [cardStates, setCardStates] = useState({});

  useEffect(() => {
    setCardStates(loadStates(sessionKey));
    setIndex(0);
    setFlipped(false);
  }, [sessionKey, list.length]);

  const current = list[index] ?? null;

  const stateForCurrent = useMemo(() => {
    if (!current) return { repetitions: 0, ease_factor: 2.5, interval_days: 0 };
    const s = cardStates[current.id];
    if (s) return s;
    return {
      repetitions: current.repetitions ?? 0,
      ease_factor: current.ease_factor ?? 2.5,
      interval_days: current.interval_days ?? 0,
    };
  }, [current, cardStates]);

  const persist = useCallback(
    (id, next) => {
      setCardStates((prev) => {
        const merged = { ...prev, [id]: next };
        saveStates(sessionKey, merged);
        return merged;
      });
    },
    [sessionKey],
  );

  const onGrade = (grade) => {
    if (!current || !flipped) return;
    const next = sm2Update(stateForCurrent, grade);
    persist(current.id, next);
    setFlipped(false);
    if (index + 1 < list.length) setIndex(index + 1);
    else setIndex(0);
  };

  if (!list.length) {
    return <p className="deck-empty">Chưa có thẻ. Hãy chạy pipeline từ audio hoặc transcript.</p>;
  }

  const againPrev = previewIntervalVi(stateForCurrent, "again");
  const hardPrev = previewIntervalVi(stateForCurrent, "hard");
  const goodPrev = previewIntervalVi(stateForCurrent, "good");
  const easyPrev = previewIntervalVi(stateForCurrent, "easy");

  return (
    <div className="deck-wrap">
      <div className="deck-toolbar">
        <span className="deck-progress">
          Thẻ {index + 1} / {list.length}
        </span>
        <span className="deck-meta">
          EF {stateForCurrent.ease_factor?.toFixed?.(2) ?? "2.50"} · Đã ôn{" "}
          {stateForCurrent.repetitions ?? 0} lần
        </span>
      </div>

      <button
        type="button"
        className={`deck-card ${flipped ? "is-back" : "is-front"}`}
        onClick={() => setFlipped(!flipped)}
        aria-label={flipped ? "Ẩn đáp án" : "Xem đáp án"}
      >
        {!flipped ? (
          <>
            <span className="deck-label">Câu hỏi</span>
            <div className="deck-tags">
              {current.card_kind ? (
                <span className="deck-kind">
                  {current.card_kind === "definition"
                    ? "Định nghĩa"
                    : current.card_kind === "connection"
                      ? "Liên hệ"
                      : "Tự kiểm tra"}
                </span>
              ) : null}
              {current.topic_tag ? <span className="deck-tag">{current.topic_tag}</span> : null}
            </div>
            <p className="deck-front-text">{current.front}</p>
            {current.source_excerpt ? (
              <blockquote className="deck-excerpt">“{current.source_excerpt}”</blockquote>
            ) : null}
            <span className="deck-hint">Chạm để lật thẻ</span>
          </>
        ) : (
          <>
            <span className="deck-label">Đáp án</span>
            <p className="deck-back-text">{current.back}</p>
            <span className="deck-hint">Chọn mức độ nhớ bên dưới (giống Anki)</span>
          </>
        )}
      </button>

      <div className="deck-grades" role="group" aria-label="Đánh giá mức độ nhớ">
        <button type="button" className="grade again" disabled={!flipped} onClick={() => onGrade("again")}>
          <span className="grade-title">Again</span>
          <span className="grade-sub">{againPrev}</span>
        </button>
        <button type="button" className="grade hard" disabled={!flipped} onClick={() => onGrade("hard")}>
          <span className="grade-title">Hard</span>
          <span className="grade-sub">{hardPrev}</span>
        </button>
        <button type="button" className="grade good" disabled={!flipped} onClick={() => onGrade("good")}>
          <span className="grade-title">Good</span>
          <span className="grade-sub">{goodPrev}</span>
        </button>
        <button type="button" className="grade easy" disabled={!flipped} onClick={() => onGrade("easy")}>
          <span className="grade-title">Easy</span>
          <span className="grade-sub">{easyPrev}</span>
        </button>
      </div>

      <p className="deck-footnote">
        Lịch ôn dùng SM-2 (SuperMemo 2), cùng họ hàng thuật toán cốt lõi của Anki. Dữ liệu lưu trên
        trình duyệt của bạn.
      </p>
    </div>
  );
}
