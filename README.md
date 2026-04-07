# YouTube & Google Drive Transcript Service

Extract transcripts from YouTube videos, playlists, and Google Drive videos. Generate AI-powered summaries using Claude Opus 4.6.

## Features

- ✅ **YouTube single video** - Extract transcript & generate summary
- ✅ **YouTube playlist** - Extract all videos, individual + combined summary
- ✅ **Google Drive single video** - Download, extract audio, transcribe with ASR
- ✅ **Google Drive folder** - Process multiple videos (requires GDrive API)
- ✅ **Multi-language support** - Summaries in any language
- ✅ **RESTful API** - FastAPI with OpenAPI docs
- ✅ **Docker-ready** - Easy deployment
- ✅ **Integrated with LiteLLM** - Model routing for Opus 4.6

## Quick Start

### 1. Setup Environment

```bash
cp .env.example .env
# Edit .env and add your LITELLM_API_KEY
# Optional: Add GDRIVE_API_KEY for folder support
```

### 2. Run with Docker

```bash
docker-compose up -d
```

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/health

# YouTube single video
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtu.be/qkW6VHPNuu8",
    "generate_summary": true,
    "summary_language": "id"
  }'

# YouTube playlist
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/playlist?list=PLexample",
    "generate_summary": true,
    "summary_language": "id",
    "combine_playlist_summary": true
  }'

# Google Drive video
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://drive.google.com/file/d/VIDEO_ID/view",
    "generate_summary": true,
    "summary_language": "id"
  }'
```

## API Endpoints

### POST `/transcribe`
Extract transcript and optionally generate summary from YouTube or Google Drive.

**Request:**
```json
{
  "url": "https://youtu.be/VIDEO_ID or https://drive.google.com/...",
  "generate_summary": true,
  "summary_language": "id",
  "combine_playlist_summary": true  // For playlists: combine all into one summary
}
```

**Response (YouTube single video):**
```json
{
  "source_type": "youtube",
  "video_id": "qkW6VHPNuu8",
  "title": "Video Title",
  "transcript": [
    {"text": "Hello everyone", "start": 0.0, "duration": 2.5}
  ],
  "full_text": "Hello everyone...",
  "summary": "AI-generated summary in Indonesian...",
  "duration_seconds": 1234.5
}
```

**Response (YouTube playlist):**
```json
{
  "source_type": "youtube_playlist",
  "video_id": "PLexample",
  "title": "Playlist: PLexample",
  "total_videos": 5,
  "video_results": [
    {
      "source_type": "youtube",
      "video_id": "abc123",
      "summary": "Summary for video 1..."
    },
    ...
  ],
  "summary": "Combined summary of all videos...",
  "duration_seconds": 5432.1
}
```

**Response (Google Drive video):**
```json
{
  "source_type": "gdrive",
  "video_id": "gdrive_file_id",
  "transcript": [{"text": "Transcribed text...", "start": 0.0, "duration": 0.0}],
  "full_text": "Transcribed text...",
  "summary": "AI-generated summary...",
  "duration_seconds": 0
}
```

### POST `/summary-only`
Generate summary from existing transcript text.

### GET `/health`
Health check endpoint.

## Supported URL Formats

### YouTube
- Single video: `https://youtu.be/VIDEO_ID`
- Single video: `https://www.youtube.com/watch?v=VIDEO_ID`
- Playlist: `https://www.youtube.com/playlist?list=PLAYLIST_ID`

### Google Drive
- Single video: `https://drive.google.com/file/d/FILE_ID/view`
- Single video: `https://drive.google.com/open?id=FILE_ID`
- Folder: `https://drive.google.com/folders/FOLDER_ID` (requires GDrive API)

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LITELLM_API_BASE` | Yes | - | LiteLLM API endpoint |
| `LITELLM_API_KEY` | Yes | - | API key for LiteLLM |
| `SUMMARY_MODEL` | No | `claude-opus-4-6` | Model for summarization |
| `EMBEDDING_MODEL` | No | `text-embedding-3-large` | Model for embeddings |
| `GDRIVE_API_KEY` | No (folder) | - | Google Drive API key for folder support |
| `YOUTUBE_API_KEY` | No (playlist) | - | YouTube Data API key for playlist support |
| `WORKSPACE_DIR` | No | `/tmp/transcript-workspace` | Temp directory for processing |

## Requirements

### System Dependencies
- **Docker** (for containerized deployment)
- **ffmpeg** (for Google Drive video processing)
- **Python 3.11+** (for local development)

### Python Dependencies
- `fastapi`
- `uvicorn`
- `youtube-transcript-api`
- `gdown` (for Google Drive download)
- `httpx`
- `pydantic`

## Limitations

### YouTube
- Requires video to have transcripts enabled (manual or auto-generated)
- Private/unlisted videos are not supported
- **NO transcript length limits** - Full transcript processed (Claude Opus 4.6 supports 1M tokens)
- Summary uses full context for comprehensive output

### Google Drive
- Video must be publicly accessible or shared with "anyone with link"
- Requires ffmpeg installed on the system
- Audio extraction may take time for large videos
- ASR transcription requires integration with speech-to-text service
- Folder support requires Google Drive API credentials

### Cost & Performance
- **NO character/token limits** - All content is processed
- Full transcript extraction for maximum accuracy
- Comprehensive summaries capture ALL rules and concepts
- Diagram generation uses complete context
- Optimized for trading education where EVERY detail matters

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Install ffmpeg (Ubuntu/Debian)
sudo apt-get install ffmpeg

# Run locally
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## ASR Integration

For Google Drive video transcription, the service supports:
- **zooclaw-asr** (if available in environment)
- **Whisper** (local model)
- **OpenAI Whisper API**

Configure ASR by setting the appropriate environment variables or integrating with your preferred ASR service.

## Example Usage

### Single YouTube Video
```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtu.be/qkW6VHPNuu8", "generate_summary": true, "summary_language": "id"}'
```

### YouTube Playlist
```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/playlist?list=PLexample",
    "generate_summary": true,
    "summary_language": "id",
    "combine_playlist_summary": true
  }'
```

### Google Drive Video
```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://drive.google.com/file/d/FILE_ID/view", "generate_summary": true, "summary_language": "id"}'
```

## License

MIT
