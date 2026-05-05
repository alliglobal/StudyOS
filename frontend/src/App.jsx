// Ứng dụng chính: nhập bài → pipeline → tổng quan / bộ thẻ kiểu Anki (SM-2) / quiz / đồ thị.
import { useMemo, useState } from "react";
import LiveTranscription from "./LiveTranscription.jsx";
import StudyDeck from "./StudyDeck.jsx";

/** Hash đơn giản để tạo khóa session bộ thẻ (localStorage) theo từng transcript. */
function hashSessionKey(transcript) {
  const s = transcript || "";
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return `deck_${s.length}_${h}`;
}

const TABS = [
  { id: "overview", label: "Tổng quan" },
  { id: "notes", label: "Lecture Notes" },
  { id: "intel", label: "AI Insights" },
  { id: "deck", label: "Bộ thẻ" },
  { id: "quiz", label: "Quiz" },
  { id: "graph", label: "Đồ thị" },
  { id: "source", label: "Transcript" },
];

export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [file, setFile] = useState(null);
  const [answers, setAnswers] = useState({});
  const [pastedText, setPastedText] = useState("");
  const [tab, setTab] = useState("overview");

  const deckKey = useMemo(() => (result ? hashSessionKey(result.transcript) : "idle"), [result]);

  const resetOutput = () => {
    setResult(null);
    setError("");
    setAnswers({});
    setTab("overview");
  };

  const onPickFile = (e) => {
    const f = e.target.files?.[0];
    setFile(f ?? null);
    resetOutput();
  };

  const onSubmitText = async () => {
    const t = pastedText.trim();
    if (!t) {
      setError("Dán hoặc nhập transcript (ít nhất vài câu).");
      return;
    }
    setLoading(true);
    setError("");
    setAnswers({});
    try {
      const res = await fetch("/api/process-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: t }),
      });
      if (!res.ok) {
        const tx = await res.text();
        throw new Error(tx || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setResult(data);
      setTab("overview");
    } catch (err) {
      setError(err?.message || "Lỗi không xác định");
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = async () => {
    if (!file) {
      setError("Vui lòng chọn file audio bài giảng.");
      return;
    }
    setLoading(true);
    setError("");
    setAnswers({});
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/process-audio", { method: "POST", body: fd });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setResult(data);
      setTab("overview");
    } catch (err) {
      setError(err?.message || "Lỗi không xác định");
    } finally {
      setLoading(false);
    }
  };

  const pickChoice = (qid, idx) => {
    setAnswers((prev) => ({ ...prev, [qid]: idx }));
  };

  const applyLiveStudyPack = (data) => {
    setResult(data);
    setAnswers({});
    setTab("overview");
  };

  const stats = result
    ? [
        { label: "Study cards", value: result.flashcards.length },
        { label: "Quiz items", value: result.quiz.length },
        { label: "Tags", value: result.semantic_tags?.length ?? 0 },
        { label: "Weak spots", value: result.weak_chunk_indices.length },
      ]
    : [];

  return (
    <div className="page">
      <header className="hero">
        <div className="hero-orb orb-a" />
        <div className="hero-orb orb-b" />
        <p className="eyebrow">VALSEA · AI learning cockpit</p>
        <h1>Phần mềm giúp việc học dễ như ăn kẹo</h1>
        <p className="lede">
          ASR thật, transcript được làm sạch, lecture notes, semantic tags, quiz cá nhân hóa và bộ
          thẻ ôn theo <strong>SM-2</strong>.
        </p>
        {result ? (
          <div className="hero-stats">
            {stats.map((s) => (
              <div key={s.label} className="hero-stat">
                <span>{s.value}</span>
                <small>{s.label}</small>
              </div>
            ))}
          </div>
        ) : null}
      </header>

      <section className="card card-input">
        <div className="input-grid">
          <div>
            <h2 className="h-inline">Audio bài giảng</h2>
            <p className="muted small">Upload → ASR (VALSEA nếu cấu hình) → pipeline.</p>
            <input
              className="file-input"
              type="file"
              accept="audio/*,.mp3,.wav,.m4a,.webm"
              onChange={onPickFile}
            />
            <div className="row">
              <button type="button" className="primary" disabled={loading} onClick={onSubmit}>
                {loading ? "Đang xử lý…" : "Chạy từ audio"}
              </button>
              <span className="hint">
                Có <code className="inline-code">VALSEA_API_KEY</code> trong <code className="inline-code">backend/.env</code>{" "}
                → ASR + Clarify + Annotate + Format + Translate.
              </span>
            </div>
          </div>
          <div className="divider" aria-hidden="true" />
          <div>
            <h2 className="h-inline">Hoặc transcript</h2>
            <p className="muted small">Bỏ qua ASR — dán nội dung đã có.</p>
            <textarea
              className="paste"
              rows={5}
              placeholder="Dán transcript vào đây…"
              value={pastedText}
              onChange={(e) => {
                setPastedText(e.target.value);
                setError("");
              }}
            />
            <button type="button" className="secondary" disabled={loading} onClick={onSubmitText}>
              {loading ? "Đang xử lý…" : "Chạy từ transcript"}
            </button>
          </div>
        </div>
        {error ? <p className="error">{error}</p> : null}
      </section>

      <LiveTranscription onStudyPack={applyLiveStudyPack} />

      {result ? (
        <>
          <nav className="tab-nav" aria-label="Khu vực ôn tập">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`tab-btn ${tab === t.id ? "active" : ""}`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </nav>

          {tab === "overview" ? (
            <div className="tab-panels">
              {result.enrichment_warnings?.length ? (
                <section className="card warning-card">
                  <h2>VALSEA enrichment warnings</h2>
                  <ul className="compact-list">
                    {result.enrichment_warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              <section className="card card-pro">
                <h2>Tóm tắt & mạch bài</h2>
                <p className="summary summary-pro">{result.summary}</p>
                {result.bilingual_summary?.english ? (
                  <div className="translation-panel">
                    <span className="panel-kicker">English version</span>
                    <p>{result.bilingual_summary.english}</p>
                  </div>
                ) : null}
              </section>

              <section className="card card-pro guide-card">
                <h2>Checklist ôn tập</h2>
                <p className="muted small">
                  Các bước có thứ tự — phù hợp active recall và spaced repetition.
                </p>
                <ol className="study-guide">
                  {result.study_guide.map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ol>
              </section>

              <section className="card card-accent">
                <h2>Điểm cần ôn kỹ</h2>
                <p className="muted small">Gợi ý từ đồ thị tri thức (ít liên kết giữa các phần).</p>
                <ul className="review-list">
                  {result.review_points.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
                <p className="muted foot">Đoạn ưu tiên: {result.weak_chunk_indices.join(", ")}</p>
              </section>
            </div>
          ) : null}

          {tab === "notes" ? (
            <div className="notes-grid">
              <section className="card note-column">
                <h2>Lecture Notes</h2>
                <ul className="premium-list">
                  {(result.formatted_notes?.lecture_notes ?? []).map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </section>
              <section className="card note-column">
                <h2>Action Items</h2>
                <ul className="premium-list check-list">
                  {(result.formatted_notes?.action_items ?? []).map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </section>
              <section className="card note-column wide">
                <h2>Key Quotes</h2>
                <div className="quote-grid">
                  {(result.formatted_notes?.key_quotes ?? []).map((item, i) => (
                    <blockquote key={i}>{item}</blockquote>
                  ))}
                </div>
              </section>
            </div>
          ) : null}

          {tab === "intel" ? (
            <div className="intel-grid">
              <section className="card">
                <h2>Semantic Tags</h2>
                {result.semantic_tags?.length ? (
                  <div className="tag-cloud">
                    {result.semantic_tags.map((tag, i) => (
                      <div key={i} className="semantic-chip">
                        <span>{tag.phrase || tag.tag}</span>
                        <small>{tag.meaning || tag.tag}</small>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="muted">Chưa có semantic tags (hoặc enrichment đang tắt).</p>
                )}
              </section>
              <section className="card">
                <h2>Clean Transcript Preview</h2>
                <p className="summary clean-preview">
                  {(result.clarified_transcript || result.transcript).slice(0, 900)}
                  {(result.clarified_transcript || result.transcript).length > 900 ? "…" : ""}
                </p>
              </section>
            </div>
          ) : null}

          {tab === "deck" ? (
            <section className="card card-deck-shell">
              <h2>Bộ thẻ — lật thẻ & chấm điểm</h2>
              <p className="muted small">
                Again / Hard / Good / Easy cập nhật khoảng cách ôn theo SM-2; trạng thái lưu trên
                trình duyệt.
              </p>
              <StudyDeck sessionKey={deckKey} flashcards={result.flashcards} />
            </section>
          ) : null}

          {tab === "quiz" ? (
            <section className="card card-pro">
              <h2>Quiz (ưu tiên phần yếu)</h2>
              {result.quiz.map((q) => {
                const picked = answers[q.id];
                const isCorrect = picked === q.correct_index;
                return (
                  <div key={q.id} className="quiz-q">
                    <p className="quiz-stem">{q.question}</p>
                    <p className="muted small">Gắn phần {q.related_chunk_index + 1}</p>
                    <div className="choices">
                      {q.choices.map((c, idx) => (
                        <label key={idx} className={`choice-tile ${picked === idx ? "picked" : ""}`}>
                          <input
                            type="radio"
                            name={q.id}
                            checked={picked === idx}
                            onChange={() => pickChoice(q.id, idx)}
                          />
                          <span>{c}</span>
                        </label>
                      ))}
                    </div>
                    {picked !== undefined ? (
                      <p className={isCorrect ? "ok" : "bad"}>
                        {isCorrect ? "Đúng." : `Sai. Đáp án đúng: “${q.choices[q.correct_index]}”.`}
                      </p>
                    ) : null}
                  </div>
                );
              })}
            </section>
          ) : null}

          {tab === "graph" ? (
            <section className="card card-pro">
              <h2>Đồ thị tri thức</h2>
              <p className="muted">
                {result.graph_nodes.length} khái niệm · {result.graph_edges.length} liên kết từ vựng
              </p>
              <div className="graph">
                {result.graph_nodes.map((n) => {
                  const neigh = result.graph_edges
                    .filter((e) => e.source === n.id || e.target === n.id)
                    .map((e) => (e.source === n.id ? e.target : e.source));
                  return (
                    <div key={n.id} className="graph-node">
                      <div className="graph-node-title">{n.id} · Phần {n.chunk_index + 1}</div>
                      <div className="graph-node-body">{n.label}</div>
                      <div className="graph-neigh">Liên kết: {neigh.join(", ") || "—"}</div>
                    </div>
                  );
                })}
              </div>
            </section>
          ) : null}

          {tab === "source" ? (
            <section className="card muted-block">
              <h2>Transcript</h2>
              <div className="source-grid">
                <div>
                  <h3>Raw ASR</h3>
                  <pre className="transcript">{result.transcript}</pre>
                </div>
                <div>
                  <h3>Clarified</h3>
                  <pre className="transcript">{result.clarified_transcript || result.transcript}</pre>
                </div>
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
