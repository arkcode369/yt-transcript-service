#!/bin/bash

# Test YouTube Transcript Service API
# Usage: ./test-api.sh [VIDEO_URL]

BASE_URL="${API_BASE_URL:-http://localhost:8000}"

if [ -z "$1" ]; then
    echo "Usage: ./test-api.sh <youtube_url>"
    echo ""
    echo "Example:"
    echo "  ./test-api.sh https://youtu.be/qkW6VHPNuu8"
    exit 1
fi

VIDEO_URL="$1"

echo "🎬 Testing YouTube Transcript Service"
echo "URL: $VIDEO_URL"
echo ""

# Test health endpoint
echo "📊 Checking service health..."
HEALTH=$(curl -s "$BASE_URL/health")
echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
echo ""

# Test transcript extraction
echo "📝 Extracting transcript and generating summary..."
RESPONSE=$(curl -s -X POST "$BASE_URL/transcribe" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"$VIDEO_URL\",
    \"generate_summary\": true,
    \"summary_language\": \"id\"
  }")

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

echo "✅ Test complete!"
