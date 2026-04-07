# YouTube Transcript Service

Extract transcripts from YouTube videos and generate AI-powered summaries using Claude Opus 4.6.

## Features

- ✅ Extract transcripts from YouTube videos
- ✅ Generate concise summaries in multiple languages
- ✅ Support for manual and auto-generated captions
- ✅ RESTful API with FastAPI
- ✅ Docker-ready deployment
- ✅ Integrated with LiteLLM for model routing

## Quick Start

### 1. Setup Environment

```bash
cp .env.example .env
# Edit .env and add your LITELLM_API_KEY
```

### 2. Run with Docker

```bash
docker-compose up -d
```

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Extract transcript and summary
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtu.be/qkW6VHPNuu8",
    "generate_summary": true,
    "summary_language": "id"
  }'
```

## API Endpoints

### POST `/transcribe`
Extract transcript and optionally generate summary.

**Request:**
```json
{
  "url": "https://youtu.be/VIDEO_ID",
  "generate_summary": true,
  "summary_language": "id"
}
```

**Response:**
```json
{
  "video_id": "qkW6VHPNuu8",
  "title": "Video Title",
  "transcript": [
    {"text": "Hello everyone", "start": 0.0, "duration": 2.5}
  ],
  "full_text": "Hello everyone...",
  "summary": "Video summary here...",
  "duration_seconds": 1234.5
}
```

### POST `/summary-only`
Generate summary from existing transcript text.

**Request:**
```json
{
  "video_id": "qkW6VHPNuu8",
  "transcript_text": "Full transcript text here...",
  "language": "id"
}
```

### GET `/health`
Health check endpoint.

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LITELLM_API_BASE` | Yes | - | LiteLLM API endpoint |
| `LITELLM_API_KEY` | Yes | - | API key for LiteLLM |
| `SUMMARY_MODEL` | No | `claude-opus-4-6` | Model for summarization |
| `EMBEDDING_MODEL` | No | `text-embedding-3-large` | Model for embeddings |

## Limitations

- Requires video to have transcripts enabled (manual or auto-generated)
- Private/unlisted videos are not supported
- Summary limited to ~15k characters of transcript
- Max summary output: 1000 tokens

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## License

MIT
