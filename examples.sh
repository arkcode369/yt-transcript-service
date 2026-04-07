#!/bin/bash

# Example usage of YouTube & Google Drive Transcript Service
# This script demonstrates how to use the API

BASE_URL="${API_BASE_URL:-http://localhost:8000}"

echo "🎬 YouTube & Google Drive Transcript Service - Examples"
echo "======================================================"
echo ""

# Function to make API call
api_call() {
    local endpoint=$1
    local data=$2
    local description=$3
    
    echo "📡 $description"
    echo "Endpoint: $endpoint"
    echo "Request: $data"
    echo ""
    
    curl -s -X POST "$BASE_URL$endpoint" \
      -H "Content-Type: application/json" \
      -d "$data" | python3 -m json.tool 2>/dev/null || curl -s -X POST "$BASE_URL$endpoint" \
      -H "Content-Type: application/json" \
      -d "$data"
    
    echo ""
    echo "---"
    echo ""
}

# Check health
echo "🔍 Checking service health..."
HEALTH=$(curl -s "$BASE_URL/health")
echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
echo ""
echo "---"
echo ""

# Example 1: YouTube single video
echo "Example 1: YouTube Single Video"
echo "================================"
api_call "/transcribe" '{
  "url": "https://youtu.be/qkW6VHPNuu8",
  "generate_summary": true,
  "summary_language": "id"
}' "Extract transcript and summary from YouTube video"

# Example 2: YouTube playlist (placeholder - needs API key)
echo "Example 2: YouTube Playlist"
echo "==========================="
api_call "/transcribe" '{
  "url": "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
  "generate_summary": true,
  "summary_language": "id",
  "combine_playlist_summary": true
}' "Extract all videos from playlist with combined summary"

# Example 3: Google Drive video
echo "Example 3: Google Drive Video"
echo "=============================="
api_call "/transcribe" '{
  "url": "https://drive.google.com/file/d/VIDEO_ID/view",
  "generate_summary": true,
  "summary_language": "id"
}' "Download, transcribe, and summarize Google Drive video"

# Example 4: Summary only
echo "Example 4: Summary Only"
echo "========================"
api_call "/summary-only" '{
  "video_id": "test",
  "transcript_text": "This is a sample transcript text for demonstration purposes. The summary will be generated based on this text.",
  "language": "id"
}' "Generate summary from existing transcript"

echo "✅ Examples complete!"
echo ""
echo "💡 Tips:"
echo "  - Replace VIDEO_ID with actual Google Drive file ID"
echo "  - For playlists, set YOUTUBE_API_KEY environment variable"
echo "  - For GDrive folders, set GDRIVE_API_KEY environment variable"
echo "  - Check service health at: $BASE_URL/health"
echo "  - API documentation at: $BASE_URL/docs"
