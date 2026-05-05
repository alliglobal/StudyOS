# VALSEA StudyOS

Turn Southeast Asian classroom audio into live transcripts, clean notes, bookmarks, flashcards, quizzes, and personalized review plans.

VALSEA StudyOS is an AI learning companion built for multilingual classrooms. It supports Vietnamese and Vietnamese-accented English, code-switching, audio upload, realtime transcription, lecture-note generation, semantic insights, and SM-2 flashcard review inspired by Anki.

## Features

- **Audio upload transcription** with VALSEA ASR.
- **Live classroom mode** with VALSEA Realtime Transcription (RTT) over WebSocket.
- **Live transcript** with partial and final segments.
- **Live notes** generated from final transcript segments.
- **Bookmarks** for important moments during class.
- **Clarified transcript** using VALSEA Clarify.
- **Lecture notes, action items, and key quotes** using VALSEA Format.
- **Semantic tags** using VALSEA Annotate.
- **Bilingual summary** using VALSEA Translate.
- **Flashcards** with SM-2 spaced repetition scheduling.
- **Quiz generation** and personalized weak-point review.
- **Knowledge graph** from transcript chunks.
- **Fallback demo mode** when no VALSEA API key is configured.

## Tech Stack

- **Frontend:** React, Vite, Web Audio API, WebSocket
- **Backend:** FastAPI, Uvicorn, httpx, websockets
- **AI API:** VALSEA ASR, RTT, Clarify, Annotate, Format, Translate

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── schemas.py
│   │   └── services/
│   │       ├── asr_service.py
│   │       ├── live_rtt_service.py
│   │       ├── valsea_nlp_service.py
│   │       ├── pipeline.py
│   │       ├── chunk_service.py
│   │       ├── summarize_service.py
│   │       ├── graph_service.py
│   │       └── quiz_service.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── LiveTranscription.jsx
│   │   ├── StudyDeck.jsx
│   │   ├── sm2.js
│   │   └── App.css
│   ├── package.json
│   └── vite.config.js
├── examples/
│   └── sample_lecture_transcript.txt
└── scripts/
    └── dev.sh
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- A VALSEA API key for real ASR / RTT / enrichment

Get an API key from the VALSEA dashboard.

## Environment Setup

Create `backend/.env`:

```env
VALSEA_API_KEY=vl_your_api_key_here
VALSEA_API_BASE=
VALSEA_LANGUAGE=vietnamese
VALSEA_ENABLE_CORRECTION=true
VALSEA_ENABLE_TAGS=true
VALSEA_RESPONSE_FORMAT=json
VALSEA_ENABLE_ENRICHMENT=true
VALSEA_TRANSLATE_TARGET=english
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Notes:

- Leave `VALSEA_API_BASE` empty to use `https://api.valsea.ai`.
- Never commit `backend/.env`.
- If `VALSEA_API_KEY` is empty, audio upload uses a mock transcript for demo mode.
- Live RTT requires a real `VALSEA_API_KEY`.

## Run Locally

From the project root:

```bash
./scripts/dev.sh
```

This starts:

- FastAPI backend at `http://127.0.0.1:8000`
- Vite frontend at `http://127.0.0.1:5173`

Open:

```text
http://127.0.0.1:5173
```

## Manual Backend Run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Manual Frontend Run

```bash
cd frontend
npm install
npm run dev
```

## Demo Flow

### Option 1: Upload Audio

1. Start the app.
2. Upload a `.wav`, `.mp3`, `.m4a`, or `.webm` lecture recording.
3. The backend calls VALSEA ASR.
4. The transcript is clarified, annotated, formatted, summarized, and converted into a study pack.
5. Review the generated tabs:
   - Overview
   - Lecture Notes
   - AI Insights
   - Flashcards
   - Quiz
   - Knowledge Graph
   - Transcript

### Option 2: Paste Transcript

Use `examples/sample_lecture_transcript.txt`, paste it into the transcript box, and run the pipeline without ASR.

### Option 3: Live RTT

1. Click **Start live**.
2. Allow microphone access.
3. Wait for **Realtime ready**.
4. Speak naturally.
5. Click **Bookmark đoạn này** during important moments.
6. Click **Stop & tạo study pack**.
7. The app generates flashcards, quiz, notes, and review points from the live transcript.

## Backend API

### Health

```http
GET /health
```

### Process Audio

```http
POST /api/process-audio
Content-Type: multipart/form-data
```

Field:

- `file`: audio file

### Process Text

```http
POST /api/process-text
Content-Type: application/json
```

Body:

```json
{
  "transcript": "Your lecture transcript here..."
}
```

### Live Transcription WebSocket

```text
WS /ws/live-transcribe
```

Client messages:

```json
{ "type": "audio", "audio": "BASE64_PCM16_16KHZ_MONO" }
```

```json
{ "type": "bookmark", "label": "Bookmark 1" }
```

```json
{ "type": "stop" }
```

Server messages include:

- `status`
- `partial`
- `final`
- `bookmark`
- `study_pack`
- `error`

## Testing

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/test_smoke.py -v
```

## Build Frontend

```bash
cd frontend
npm run build
```

## How It Works

```text
Audio / Live Mic / Transcript
        ↓
VALSEA ASR or VALSEA RTT
        ↓
Clarify + Annotate + Format + Translate
        ↓
Chunking + Summarization
        ↓
Knowledge Graph + Weak Spot Detection
        ↓
Flashcards + Quiz + Study Guide
```

## Why It Matters

Many Southeast Asian classrooms are multilingual in practice. Students often hear Vietnamese, English technical terms, local examples, and accented speech in the same lesson. Generic AI systems often struggle with this language layer.

VALSEA StudyOS turns that messy classroom audio into structured learning materials students can actually review.

## Future Improvements

- Export flashcards to Anki.
- Export notes to Notion or Google Docs.
- Teacher dashboard for class-level weak spots.
- Student progress history across multiple lessons.
- Better semantic graph layout.
- LMS integration for Moodle, Canvas, or Google Classroom.

## License

MIT
