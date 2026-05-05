import { useRef, useState } from "react";

function wsUrl() {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/live-transcribe`;
}

function floatTo16kBase64(float32, sourceRate) {
  const targetRate = 16000;
  const ratio = sourceRate / targetRate;
  const length = Math.floor(float32.length / ratio);
  const pcm = new Int16Array(length);
  for (let i = 0; i < length; i += 1) {
    const srcIndex = Math.floor(i * ratio);
    const sample = Math.max(-1, Math.min(1, float32[srcIndex] || 0));
    pcm[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  const bytes = new Uint8Array(pcm.buffer);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

export default function LiveTranscription({ onStudyPack }) {
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("Sẵn sàng ghi realtime.");
  const [partial, setPartial] = useState("");
  const [segments, setSegments] = useState([]);
  const [notes, setNotes] = useState([]);
  const [bookmarks, setBookmarks] = useState([]);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);

  const wsRef = useRef(null);
  const audioRef = useRef(null);
  const streamRef = useRef(null);
  const sourceRef = useRef(null);
  const processorRef = useRef(null);
  const timerRef = useRef(null);
  const startedAtRef = useRef(0);
  const readyRef = useRef(false);

  const start = async () => {
    setError("");
    setSegments([]);
    setNotes([]);
    setBookmarks([]);
    setPartial("");
    setElapsed(0);
    setStatus("connecting");
    setMessage("Đang xin quyền microphone...");
    readyRef.current = false;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      const socket = new WebSocket(wsUrl());

      streamRef.current = stream;
      audioRef.current = audioCtx;
      sourceRef.current = source;
      processorRef.current = processor;
      wsRef.current = socket;

      socket.onopen = () => {
        setStatus("connecting");
        setMessage("Đã mở WebSocket, đang chờ VALSEA báo session.ready...");
        startedAtRef.current = Date.now();
        timerRef.current = window.setInterval(() => {
          setElapsed(Math.floor((Date.now() - startedAtRef.current) / 1000));
        }, 1000);

        processor.onaudioprocess = (event) => {
          if (socket.readyState !== WebSocket.OPEN) return;
          if (!readyRef.current) return;
          const input = event.inputBuffer.getChannelData(0);
          const audio = floatTo16kBase64(input, audioCtx.sampleRate);
          socket.send(JSON.stringify({ type: "audio", audio }));
        };
        source.connect(processor);
        processor.connect(audioCtx.destination);
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "status") {
          setMessage(data.message || data.status);
          if (data.status === "ready") {
            readyRef.current = true;
            setStatus("live");
          }
          if (data.status === "connecting" || data.status === "created") setStatus("connecting");
          if (data.status === "processing") setStatus("processing");
        } else if (data.type === "partial") {
          setPartial(data.text || "");
        } else if (data.type === "final") {
          const text = (data.text || "").trim();
          if (text) setSegments((prev) => [...prev, text]);
          if (data.live_note) setNotes((prev) => [...prev, data.live_note]);
          setPartial("");
        } else if (data.type === "bookmark") {
          setBookmarks((prev) => [...prev, data.bookmark]);
        } else if (data.type === "study_pack") {
          setStatus("done");
          setMessage("Đã tạo flashcards/quiz từ phiên realtime.");
          setBookmarks(data.bookmarks || []);
          onStudyPack?.(data.result);
          cleanupAudio();
        } else if (data.type === "study_pack_error") {
          setStatus("idle");
          setError(data.message || "Không tạo được study pack.");
          cleanupAudio();
        } else if (data.type === "error") {
          setStatus("error");
          setError(data.message || "Realtime error");
          cleanupAudio();
        }
      };

      socket.onerror = () => {
        setStatus("error");
        setError("WebSocket realtime bị lỗi.");
        cleanupAudio();
      };
      socket.onclose = () => {
        if (status === "live") setStatus("idle");
        cleanupAudio();
      };
    } catch (err) {
      setStatus("error");
      setError(err?.message || "Không mở được microphone.");
      cleanupAudio();
    }
  };

  const stop = () => {
    setStatus("processing");
    setMessage("Đang chốt transcript và tạo study pack...");
    const socket = wsRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "commit" }));
      socket.send(JSON.stringify({ type: "stop" }));
    }
    readyRef.current = false;
    cleanupAudio(false);
  };

  const bookmark = () => {
    const socket = wsRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "bookmark", label: `Bookmark ${bookmarks.length + 1}` }));
    }
  };

  const cleanupAudio = (closeSocket = true) => {
    if (timerRef.current) window.clearInterval(timerRef.current);
    timerRef.current = null;
    readyRef.current = false;
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    streamRef.current?.getTracks()?.forEach((track) => track.stop());
    if (audioRef.current?.state !== "closed") audioRef.current?.close?.();
    processorRef.current = null;
    sourceRef.current = null;
    streamRef.current = null;
    audioRef.current = null;
    if (closeSocket && wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.close();
  };

  const liveText = [...segments, partial].filter(Boolean).join(" ");
  const isLive = status === "live" || status === "connecting";

  return (
    <section className="card live-shell">
      <div className="live-head">
        <div>
          <p className="eyebrow live-eyebrow">Realtime RTT</p>
          <h2>Live Classroom Mode</h2>
          <p className="muted small">
            Mic → PCM16 16kHz → VALSEA RTT → transcript live → stop để tự tạo flashcards/quiz.
          </p>
        </div>
        <div className={`live-pill ${status}`}>
          <span className="pulse-dot" />
          {status} · {elapsed}s
        </div>
      </div>

      <div className="live-actions">
        {!isLive && status !== "processing" ? (
          <button type="button" className="primary" onClick={start}>
            Start live
          </button>
        ) : (
          <button type="button" className="danger-btn" onClick={stop} disabled={status === "processing"}>
            Stop & tạo study pack
          </button>
        )}
        <button type="button" className="secondary" onClick={bookmark} disabled={!isLive}>
          Bookmark đoạn này
        </button>
        <span className="hint">{message}</span>
      </div>

      {error ? <p className="error">{error}</p> : null}

      <div className="live-grid">
        <div className="live-panel transcript-panel">
          <h3>Transcript live</h3>
          <div className="live-transcript">
            {liveText || "Bấm Start live rồi nói thử 1-2 câu..."}
            {partial ? <span className="partial-text"> {partial}</span> : null}
          </div>
        </div>

        <div className="live-panel">
          <h3>Note live</h3>
          <ul className="live-list">
            {notes.length ? notes.map((n, i) => <li key={i}>{n}</li>) : <li>Final segments sẽ thành note ở đây.</li>}
          </ul>
        </div>

        <div className="live-panel wide">
          <h3>Bookmarks</h3>
          <div className="bookmark-row">
            {bookmarks.length ? (
              bookmarks.map((b) => (
                <div key={b.id} className="bookmark-card">
                  <strong>{b.label}</strong>
                  <small>{b.elapsedSec}s</small>
                  <p>{b.text || "Đã đánh dấu đoạn hiện tại."}</p>
                </div>
              ))
            ) : (
              <p className="muted">Khi giảng viên nói đoạn quan trọng, bấm “Bookmark đoạn này”.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
