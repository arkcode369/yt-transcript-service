"""
YouTube Transcript Service
Extracts transcripts from YouTube videos and generates summaries using AI.
"""

import os
import asyncio
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YouTube Transcript Service",
    description="Extract transcripts and generate summaries from YouTube videos",
    version="1.0.0"
)

# Configuration
LITELLM_API_BASE = os.getenv("LITELLM_API_BASE", "https://litellm.vllm.yesy.online/v1")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "claude-opus-4-6")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

# Cache for transcripts
transcript_cache = {}


class TranscriptRequest(BaseModel):
    url: str
    generate_summary: bool = True
    summary_language: str = "id"  # Default to Indonesian


class TranscriptResponse(BaseModel):
    video_id: str
    title: Optional[str] = None
    transcript: List[dict]
    full_text: str
    summary: Optional[str] = None
    duration_seconds: float


class SummaryRequest(BaseModel):
    video_id: str
    transcript_text: str
    language: str = "id"


async def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL."""
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    elif "watch?v=" in url:
        return url.split("watch?v=")[-1].split("&")[0]
    else:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")


async def get_transcript(video_id: str) -> List[dict]:
    """Fetch transcript from YouTube."""
    if video_id in transcript_cache:
        logger.info(f"Returning cached transcript for {video_id}")
        return transcript_cache[video_id]
    
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_cache[video_id] = transcript
        return transcript
    except NoTranscriptFound:
        raise HTTPException(status_code=404, detail="No transcript found for this video")
    except TranscriptsDisabled:
        raise HTTPException(status_code=403, detail="Transcripts are disabled for this video")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract transcript: {str(e)}")


async def generate_summary(transcript_text: str, language: str) -> str:
    """Generate summary using LiteLLM with Opus 4.6."""
    if not LITELLM_API_KEY:
        logger.warning("LITELLM_API_KEY not set, skipping summary generation")
        return "Summary generation skipped: API key not configured"
    
    prompt = f"""
    Please summarize the following YouTube video transcript in {language} language.
    
    Guidelines:
    - Create a concise summary (2-3 paragraphs)
    - Highlight key points and main ideas
    - Maintain the original context and meaning
    - Use natural, flowing language
    
    Transcript:
    {transcript_text[:15000]}  # Limit to 15k chars to avoid token limits
    
    Summary:
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
                            "content": "You are a helpful assistant that summarizes video transcripts."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.7
                },
                timeout=60.0
            )
            
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            return f"Summary generation failed: {str(e)}"


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "YouTube Transcript Service",
        "status": "running",
        "endpoints": {
            "/transcribe": "Extract transcript from YouTube video",
            "/summary": "Generate summary from transcript text"
        }
    }


@app.post("/transcribe", response_model=TranscriptResponse)
async def transcribe_video(request: TranscriptRequest, background_tasks: BackgroundTasks):
    """
    Extract transcript from YouTube video and optionally generate summary.
    """
    try:
        video_id = await extract_video_id(request.url)
        logger.info(f"Processing video: {video_id}")
        
        # Extract transcript
        transcript = await get_transcript(video_id)
        
        # Format full text
        full_text = " ".join([entry["text"] for entry in transcript])
        duration_seconds = sum(entry["duration"] for entry in transcript)
        
        # Generate summary if requested
        summary = None
        if request.generate_summary and full_text:
            summary = await generate_summary(full_text, request.summary_language)
        
        return TranscriptResponse(
            video_id=video_id,
            transcript=transcript,
            full_text=full_text,
            summary=summary,
            duration_seconds=duration_seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


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
        "transcript_api": "available",
        "summary_model": SUMMARY_MODEL,
        "cache_size": len(transcript_cache)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
