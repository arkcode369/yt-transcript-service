#!/bin/bash

# YouTube Transcript Service Deployment Script
# This script deploys the service using Docker

set -e

echo "🚀 Deploying YouTube Transcript Service..."

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo "❌ Docker Compose is not installed."
    exit 1
fi

# Setup environment
if [ ! -f .env ]; then
    echo "📝 Setting up environment..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your LITELLM_API_KEY"
    exit 1
fi

# Build and run
echo "🔨 Building Docker image..."
$COMPOSE_CMD build

echo "🏃 Starting service..."
$COMPOSE_CMD up -d

echo "✅ Service deployed successfully!"
echo ""
echo "📊 Access points:"
echo "   - API: http://localhost:8000"
echo "   - Docs: http://localhost:8000/docs"
echo "   - Health: http://localhost:8000/health"
echo ""
echo "📝 Example usage:"
echo '   curl -X POST "http://localhost:8000/transcribe" \\'
echo '     -H "Content-Type: application/json" \\'
echo '     -d '{"'"'url'"'"':"'"'https://youtu.be/VIDEO_ID'"'"',"'"'generate_summary'"'"':true}'
echo ""
echo "📖 View logs:"
echo "   $COMPOSE_CMD logs -f"
echo ""
echo "🛑 Stop service:"
echo "   $COMPOSE_CMD down"
