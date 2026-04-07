"""
YouTube & Google Drive Transcript Service
Extracts transcripts from YouTube videos, playlists, and Google Drive videos.
Generates summaries and diagrams using AI.
"""

import os
import asyncio
import re
import json
import tempfile
import subprocess
from typing import Optional, List, Dict, Any
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from youtube_transcript_api._errors import YouTubeTranscriptApiError
import httpx
import logging
import gdown

# Import diagram generator
from diagram_generator import DiagramGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YouTube & Google Drive Transcript Service",
    description="Extract transcripts and generate summaries from YouTube videos, playlists, and Google Drive videos",
    version="2.0.0"
)

# Configuration
LITELLM_API_BASE = os.getenv("LITELLM_API_BASE", "https://litellm.vllm.yesy.online/v1")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "claude-opus-4-6")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", "/tmp/transcript-workspace")

# Ensure workspace directory exists
Path(WORKSPACE_DIR).mkdir(parents=True, exist_ok=True)

# Cache for transcripts
transcript_cache = {}

# Initialize diagram generator
diagram_generator = DiagramGenerator(
    litellm_api_base=LITELLM_API_BASE,
    litellm_api_key=LITELLM_API_KEY,
    model=SUMMARY_MODEL
)


class TranscriptRequest(BaseModel):
    url: str
    generate_summary: bool = True
    summary_language: str = "id"
    combine_playlist_summary: bool = True  # For playlists: combine all into one summary
    generate_diagrams: bool = True  # Generate Mermaid diagrams
    diagram_types: Optional[List[str]] = None  # Specific types: flowchart, mindmap, timeline, sequence


class VideoTranscript(BaseModel):
    video_id: str
    title: Optional[str] = None
    transcript: List[dict]
    full_text: str
    duration_seconds: float


class TranscriptResponse(BaseModel):
    source_type: str  # "youtube", "youtube_playlist", "gdrive", "gdrive_folder"
    video_id: str
    title: Optional[str] = None
    transcript: List[dict]
    full_text: str
    summary: Optional[str] = None
    duration_seconds: float
    # For playlists/folders
    total_videos: int = 1
    video_results: Optional[List['TranscriptResponse']] = None
    # Diagrams
    diagrams: Optional[Dict[str, Any]] = None  # Generated Mermaid diagrams


class SummaryRequest(BaseModel):
    video_id: str
    transcript_text: str
    language: str = "id"


# ==================== YouTube Functions ====================

async def extract_youtube_video_id(url: str) -> str:
    """Extract video ID from YouTube URL."""
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    elif "watch?v=" in url:
        return url.split("watch?v=")[-1].split("&")[0]
    elif "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    else:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")


async def extract_youtube_playlist_id(url: str) -> str:
    """Extract playlist ID from YouTube URL."""
    if "list=" in url:
        return url.split("list=")[-1].split("&")[0]
    else:
        raise HTTPException(status_code=400, detail="Invalid YouTube playlist URL")


async def get_youtube_transcript(video_id: str) -> List[dict]:
    """Fetch transcript from YouTube."""
    if video_id in transcript_cache:
        logger.info(f"Returning cached transcript for {video_id}")
        return transcript_cache[video_id]
    
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_cache[video_id] = transcript
        return transcript
    except NoTranscriptFound:
        raise HTTPException(status_code=404, detail=f"No transcript found for video {video_id}")
    except TranscriptsDisabled:
        raise HTTPException(status_code=403, detail=f"Transcripts are disabled for video {video_id}")
    except YouTubeTranscriptApiError as e:
        raise HTTPException(status_code=500, detail=f"YouTube API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract transcript: {str(e)}")


async def get_playlist_videos(playlist_id: str) -> List[str]:
    """Get all video IDs from a YouTube playlist."""
    # This is a simplified version - in production, use YouTube Data API
    # For now, we'll use a workaround with the transcript API
    video_ids = []
    
    # Note: This requires YouTube Data API key for proper implementation
    # For demo purposes, we'll return a placeholder
    logger.warning("Playlist extraction requires YouTube Data API key")
    logger.warning("For full playlist support, set YOUTUBE_API_KEY environment variable")
    
    # TODO: Implement proper playlist extraction with YouTube Data API
    # For now, return empty list
    return video_ids


# ==================== Google Drive Functions ====================

async def extract_gdrive_file_id(url: str) -> str:
    """Extract file ID from Google Drive URL."""
    # Pattern: https://drive.google.com/file/d/FILE_ID/view
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    
    # Pattern: https://drive.google.com/open?id=FILE_ID
    match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    
    raise HTTPException(status_code=400, detail="Invalid Google Drive URL")


async def download_gdrive_file(file_id: str, output_path: str) -> str:
    """Download file from Google Drive."""
    url = f"https://drive.google.com/uc?id={file_id}"
    
    try:
        gdown.download(url, output_path, quiet=False)
        return output_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download GDrive file: {str(e)}")


async def extract_audio_from_video(video_path: str, audio_path: str) -> str:
    """Extract audio from video using ffmpeg."""
    try:
        cmd = [
            'ffmpeg', '-i', video_path,
            '-q:a', '0',
            '-map', 'a',
            '-y',  # Overwrite
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Failed to extract audio: {result.stderr}")
        
        return audio_path
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Audio extraction timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="FFmpeg not installed. Please install ffmpeg.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract audio: {str(e)}")


async def transcribe_audio_with_asr(audio_path: str) -> str:
    """Transcribe audio using zooclaw-asr or Whisper."""
    # For now, we'll use a placeholder
    # In production, integrate with zooclaw-asr API or Whisper
    
    logger.info(f"Transcribing audio: {audio_path}")
    
    # TODO: Implement actual ASR transcription
    # Options:
    # 1. Use zooclaw-asr skill (if available)
    # 2. Use Whisper local model
    # 3. Use OpenAI Whisper API
    
    # Placeholder: Return empty transcript
    # In production, replace with actual transcription
    transcript = "Audio transcription service not configured. Please integrate ASR service."
    
    return transcript


async def process_gdrive_video(url: str, language: str) -> VideoTranscript:
    """Process a single Google Drive video file."""
    file_id = await extract_gdrive_file_id(url)
    
    # Create temp directory for this video
    temp_dir = Path(WORKSPACE_DIR) / f"gdrive_{file_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    video_path = temp_dir / "video.mp4"
    audio_path = temp_dir / "audio.mp3"
    
    try:
        # Download video
        logger.info(f"Downloading GDrive video: {file_id}")
        await download_gdrive_file(file_id, str(video_path))
        
        # Extract audio
        logger.info("Extracting audio from video...")
        await extract_audio_from_video(str(video_path), str(audio_path))
        
        # Transcribe audio
        logger.info("Transcribing audio...")
        full_text = await transcribe_audio_with_asr(str(audio_path))
        
        # Create fake transcript format
        transcript = [{"text": full_text, "start": 0.0, "duration": 0.0}]
        
        return VideoTranscript(
            video_id=file_id,
            title=None,
            transcript=transcript,
            full_text=full_text,
            duration_seconds=0.0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process GDrive video: {str(e)}")
    finally:
        # Cleanup temp files
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


# ==================== Summary Functions ====================

async def generate_summary(transcript_text: str, language: str) -> str:
    """Generate summary using LiteLLM with Opus 4.6."""
    if not LITELLM_API_KEY:
        logger.warning("LITELLM_API_KEY not set, skipping summary generation")
        return "Summary generation skipped: API key not configured"
    
    # NO TRUNCATION for trading - all content is important
    # But we'll let the model handle long context (Opus supports 1M tokens)
    
    prompt = f"""
    CRITICAL: This is TRADING EDUCATION content. EVERY concept, rule, and principle is IMPORTANT.
    
    Please create a COMPREHENSIVE summary of this trading video transcript in {language} language.
    
    Guidelines:
    1. Capture ALL key concepts taught by the mentor
    2. EXPLICITLY state all RULES and conditions (e.g., "always do X", "never do Y", "if A then B")
    3. Highlight entry/exit rules, risk management rules, and psychological principles
    4. Maintain the original context and meaning
    5. Be thorough - trading requires DISCIPLINE and understanding ALL concepts
    6. Structure: Main strategy → Rules → Risk management → Psychology
    
    IMPORTANT: Do NOT skip any important concept. Trading success depends on following ALL rules consistently.
    
    Transcript:
    {transcript_text}
    
    Comprehensive Summary:
    """
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{LITELLM_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LITELLM_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": SUMMARY_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a trading education expert. Create comprehensive summaries that capture ALL rules and concepts."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 0,  # No limit - comprehensive summary
                    "temperature": 0.6
                },
                timeout=120.0
            )
            
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            return f"Summary generation failed: {str(e)}"


async def generate_combined_summary(video_summaries: List[str], language: str) -> str:
    """Generate a combined summary for multiple videos."""
    if not video_summaries:
        return "No summaries to combine"
    
    combined_text = "\n\n---\n\n".join(video_summaries)
    
    prompt = f"""
    CRITICAL: These are TRADING EDUCATION videos. EVERY rule, concept, and principle across ALL videos is IMPORTANT.
    
    Please create a COMPREHENSIVE combined summary of the following trading video transcripts in {language} language.
    
    Guidelines:
    1. Capture ALL key concepts from ALL videos - nothing should be omitted
    2. EXPLICITLY state all RULES that appear across videos
    3. Identify common themes and how concepts build on each other
    4. Highlight the complete trading system/strategy taught
    5. Include: strategy rules, risk management, psychology, execution flow
    6. Structure logically: Overview → Strategy → Rules → Risk → Psychology
    
    IMPORTANT: Trading requires DISCIPLINE. The combined summary must be complete so the trader can follow ALL rules consistently.
    
    Individual Video Summaries:
    {combined_text}
    
    Comprehensive Combined Summary:
    """
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{LITELLM_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LITELLM_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": SUMMARY_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a trading education expert. Create comprehensive combined summaries capturing ALL rules and concepts."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 0,  # No limit - full combined summary
                    "temperature": 0.6
                },
                timeout=180.0
            )
            
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Combined summary generation failed: {str(e)}")
            return f"Combined summary generation failed: {str(e)}"


# ==================== API Endpoints ====================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "YouTube & Google Drive Transcript Service",
        "status": "running",
        "version": "2.0.0",
        "supported_sources": [
            "YouTube single video",
            "YouTube playlist",
            "Google Drive single video",
            "Google Drive folder (multiple videos)"
        ],
        "endpoints": {
            "/transcribe": "Extract transcript from video/playlist",
            "/summary": "Generate summary from transcript text",
            "/health": "Health check"
        }
    }


@app.post("/transcribe", response_model=TranscriptResponse)
async def transcribe_video(request: TranscriptRequest, background_tasks: BackgroundTasks):
    """
    Extract transcript from YouTube video/playlist or Google Drive video/folder.
    """
    url = request.url
    
    # Detect source type
    if "youtube.com" in url or "youtu.be" in url:
        # Check if it's a playlist
        if "list=" in url:
            return await transcribe_youtube_playlist(request)
        else:
            return await transcribe_youtube_video(request)
    elif "drive.google.com" in url:
        # Check if it's a folder
        if "/folders/" in url:
            return await transcribe_gdrive_folder(request)
        else:
            return await transcribe_gdrive_video(request)
    else:
        raise HTTPException(status_code=400, detail="Unsupported URL format. Use YouTube or Google Drive links.")


async def transcribe_youtube_video(request: TranscriptRequest) -> TranscriptResponse:
    """Transcribe a single YouTube video."""
    try:
        video_id = await extract_youtube_video_id(request.url)
        logger.info(f"Processing YouTube video: {video_id}")
        
        # Extract transcript
        transcript = await get_youtube_transcript(video_id)
        
        # Format full text
        full_text = " ".join([entry["text"] for entry in transcript])
        duration_seconds = sum(entry["duration"] for entry in transcript)
        
        # Generate summary if requested
        summary = None
        if request.generate_summary and full_text:
            summary = await generate_summary(full_text, request.summary_language)
        
        # Generate diagrams if requested
        diagrams = None
        if request.generate_diagrams and full_text:
            try:
                logger.info("Generating diagrams...")
                diagram_result = await diagram_generator.generate_all_diagrams(
                    full_text,
                    video_id  # Use video_id as title
                )
                diagrams = diagram_result
            except Exception as e:
                logger.error(f"Diagram generation failed: {str(e)}")
                diagrams = {"error": f"Diagram generation failed: {str(e)}"}
        
        return TranscriptResponse(
            source_type="youtube",
            video_id=video_id,
            transcript=transcript,
            full_text=full_text,
            summary=summary,
            duration_seconds=duration_seconds,
            diagrams=diagrams
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


async def transcribe_youtube_playlist(request: TranscriptRequest) -> TranscriptResponse:
    """Transcribe a YouTube playlist."""
    try:
        playlist_id = await extract_youtube_playlist_id(request.url)
        logger.info(f"Processing YouTube playlist: {playlist_id}")
        
        # Get all video IDs in playlist
        video_ids = await get_playlist_videos(playlist_id)
        
        if not video_ids:
            raise HTTPException(status_code=404, detail="No videos found in playlist or YouTube Data API not configured")
        
        logger.info(f"Found {len(video_ids)} videos in playlist")
        
        # Process each video
        video_results = []
        individual_summaries = []
        all_transcript_text = ""
        
        for i, video_id in enumerate(video_ids):
            logger.info(f"Processing video {i+1}/{len(video_ids)}: {video_id}")
            
            try:
                transcript = await get_youtube_transcript(video_id)
                full_text = " ".join([entry["text"] for entry in transcript])
                duration = sum(entry["duration"] for entry in transcript)
                
                video_result = TranscriptResponse(
                    source_type="youtube",
                    video_id=video_id,
                    transcript=transcript,
                    full_text=full_text,
                    summary=None,
                    duration_seconds=duration
                )
                video_results.append(video_result)
                
                # Collect for combined summary
                individual_summaries.append(f"Video {video_id}: {full_text[:1000]}...")
                all_transcript_text += f"\n\n=== Video {video_id} ===\n{full_text}"
                
            except Exception as e:
                logger.error(f"Failed to process video {video_id}: {str(e)}")
                continue
        
        if not video_results:
            raise HTTPException(status_code=500, detail="Failed to process any videos in playlist")
        
        # Generate individual summaries
        if request.generate_summary:
            for video_result in video_results:
                if video_result.full_text:
                    video_result.summary = await generate_summary(video_result.full_text, request.summary_language)
        
        # Generate combined summary if requested
        combined_summary = None
        if request.generate_summary and request.combine_playlist_summary and individual_summaries:
            combined_summary = await generate_combined_summary(individual_summaries, request.summary_language)
        
        return TranscriptResponse(
            source_type="youtube_playlist",
            video_id=playlist_id,
            title=f"Playlist: {playlist_id}",
            transcript=[],
            full_text=all_transcript_text,
            summary=combined_summary,
            duration_seconds=sum(v.duration_seconds for v in video_results),
            total_videos=len(video_results),
            video_results=video_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Playlist processing failed: {str(e)}")


async def transcribe_gdrive_video(request: TranscriptRequest) -> TranscriptResponse:
    """Transcribe a single Google Drive video."""
    try:
        logger.info(f"Processing Google Drive video: {request.url}")
        
        video_transcript = await process_gdrive_video(request.url, request.summary_language)
        
        # Generate summary if requested
        summary = None
        if request.generate_summary and video_transcript.full_text:
            summary = await generate_summary(video_transcript.full_text, request.summary_language)
        
        return TranscriptResponse(
            source_type="gdrive",
            video_id=video_transcript.video_id,
            transcript=video_transcript.transcript,
            full_text=video_transcript.full_text,
            summary=summary,
            duration_seconds=video_transcript.duration_seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GDrive processing failed: {str(e)}")


async def transcribe_gdrive_folder(request: TranscriptRequest) -> TranscriptResponse:
    """Transcribe all videos in a Google Drive folder."""
    try:
        folder_id = await extract_gdrive_file_id(request.url)
        logger.info(f"Processing Google Drive folder: {folder_id}")
        
        # TODO: Implement folder listing with Google Drive API
        # For now, return placeholder
        raise HTTPException(
            status_code=501,
            detail="Google Drive folder processing requires Google Drive API integration. Please configure GDRIVE_API_KEY environment variable."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Folder processing failed: {str(e)}")


@app.post("/summary-only")
async def summary_only(request: SummaryRequest):
    """
    Generate summary from existing transcript text.
    """
    if not request.transcript_text:
        raise HTTPException(status_code=400, detail="Transcript text is required")
    
    summary = await generate_summary(request.transcript_text, request.language)
    
    return {
        "video_id": request.video_id,
        "summary": summary
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "transcript_api": "available",
        "summary_model": SUMMARY_MODEL,
        "cache_size": len(transcript_cache),
        "workspace_dir": WORKSPACE_DIR
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
