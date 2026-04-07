"""
Diagram Generator for Trading Videos
Generates Mermaid.js diagrams from video transcripts
"""

import logging
from typing import Dict, List, Optional, Tuple
import httpx

logger = logging.getLogger(__name__)

# Trading-specific diagram templates
FLOWCHART_TEMPLATE = """
graph TD
    {}
    
    style {} fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style {} fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style {} fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
"""

MINDMAP_TEMPLATE = """
mindmap
  root(({}))
    {}
"""

TIMELINE_TEMPLATE = """
timeline
    title {}
    {}
"""

SEQUENCE_TEMPLATE = """
sequenceDiagram
    {}
"""

class DiagramGenerator:
    """Generate Mermaid diagrams from trading video transcripts"""
    
    def __init__(self, litellm_api_base: str, litellm_api_key: str, model: str = "claude-opus-4-6"):
        self.api_base = litellm_api_base
        self.api_key = litellm_api_key
        self.model = model
    
    async def analyze_content_type(self, transcript_text: str) -> str:
        """Analyze transcript to determine best diagram types"""
        
        prompt = f"""
        Analyze this trading video transcript and determine the best diagram types to represent the content.
        
        Available diagram types:
        - flowchart: For trading systems, decision processes, entry/exit rules
        - mindmap: For trading concepts, strategies, knowledge structures
        - timeline: For daily/weekly reviews, trading schedules, event sequences
        - sequence: For trade execution flows, system interactions
        - gantt: For trading plans, position management over time
        
        Transcript:
        {transcript_text[:10000]}
        
        Return JSON format:
        {{
            "primary_type": "flowchart|mindmap|timeline|sequence|gantt",
            "secondary_types": ["mindmap", "timeline"],
            "confidence": 0.95,
            "reasoning": "Brief explanation"
        }}
        """
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are a diagram expert specializing in trading content."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 500,
                        "temperature": 0.3
                    },
                    timeout=60.0
                )
                
                response.raise_for_status()
                data = response.json()
                import json
                result = json.loads(data["choices"][0]["message"]["content"])
                return result
                
            except Exception as e:
                logger.error(f"Content analysis failed: {str(e)}")
                return {
                    "primary_type": "flowchart",
                    "secondary_types": ["mindmap"],
                    "confidence": 0.5,
                    "reasoning": "Default to flowchart"
                }
    
    async def generate_flowchart(self, transcript_text: str, title: str = "Trading System Flow") -> str:
        """Generate flowchart diagram for trading systems"""
        
        prompt = f"""
        Create a Mermaid.js flowchart from this trading video transcript.
        Focus on: decision points, entry/exit rules, risk management steps.
        
        Format: Pure Mermaid.js code only, no markdown formatting.
        
        Transcript:
        {transcript_text[:8000]}
        
        Generate flowchart with:
        - Start/End nodes (rounded rectangles)
        - Decision points (diamonds)
        - Process steps (rectangles)
        - Clear labels and connections
        
        Output ONLY the Mermaid code:
        """
        
        mermaid_code = await self._call_llm(prompt)
        
        # Clean up the code
        mermaid_code = mermaid_code.strip()
        if mermaid_code.startswith('```mermaid'):
            mermaid_code = mermaid_code.split('```mermaid')[1].split('```')[0].strip()
        if mermaid_code.startswith('graph'):
            pass  # Already correct
        else:
            mermaid_code = f"graph TD\n{mermaid_code}"
        
        return mermaid_code
    
    async def generate_mindmap(self, transcript_text: str, center_topic: str = "Trading Strategy") -> str:
        """Generate mindmap for trading concepts"""
        
        prompt = f"""
        Create a Mermaid.js mindmap from this trading video transcript.
        Extract key concepts, strategies, and their relationships.
        
        Format: Pure Mermaid.js code only.
        
        Transcript:
        {transcript_text[:8000]}
        
        Output ONLY the Mermaid code:
        """
        
        mermaid_code = await self._call_llm(prompt)
        
        mermaid_code = mermaid_code.strip()
        if mermaid_code.startswith('```mermaid'):
            mermaid_code = mermaid_code.split('```mermaid')[1].split('```')[0].strip()
        if not mermaid_code.startswith('mindmap'):
            mermaid_code = f"mindmap\n  root(({center_topic}))\n{mermaid_code}"
        
        return mermaid_code
    
    async def generate_timeline(self, transcript_text: str, title: str = "Trading Review Timeline") -> str:
        """Generate timeline for trading reviews"""
        
        prompt = f"""
        Create a Mermaid.js timeline from this trading video transcript.
        Extract dates, times, events, and trading activities.
        
        Format: Pure Mermaid.js code only.
        
        Transcript:
        {transcript_text[:8000]}
        
        Output ONLY the Mermaid code:
        """
        
        mermaid_code = await self._call_llm(prompt)
        
        mermaid_code = mermaid_code.strip()
        if mermaid_code.startswith('```mermaid'):
            mermaid_code = mermaid_code.split('```mermaid')[1].split('```')[0].strip()
        if not mermaid_code.startswith('timeline'):
            mermaid_code = f"timeline\n    title {title}\n{mermaid_code}"
        
        return mermaid_code
    
    async def generate_sequence(self, transcript_text: str, title: str = "Trade Execution Flow") -> str:
        """Generate sequence diagram for trading processes"""
        
        prompt = f"""
        Create a Mermaid.js sequence diagram from this trading video transcript.
        Show interactions between trader, platform, broker, risk systems.
        
        Format: Pure Mermaid.js code only.
        
        Transcript:
        {transcript_text[:8000]}
        
        Output ONLY the Mermaid code:
        """
        
        mermaid_code = await self._call_llm(prompt)
        
        mermaid_code = mermaid_code.strip()
        if mermaid_code.startswith('```mermaid'):
            mermaid_code = mermaid_code.split('```mermaid')[1].split('```')[0].strip()
        if not mermaid_code.startswith('sequenceDiagram'):
            mermaid_code = f"sequenceDiagram\n    {mermaid_code}"
        
        return mermaid_code
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM to generate diagram code"""
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an expert at creating Mermaid.js diagrams from text."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 1500,
                        "temperature": 0.4
                    },
                    timeout=90.0
                )
                
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
            except Exception as e:
                logger.error(f"Diagram generation failed: {str(e)}")
                return f"<!-- Diagram generation failed: {str(e)} -->\ngraph TD\n    A[Error] --> B[Check logs]"
    
    async def generate_all_diagrams(self, transcript_text: str, video_title: str = "") -> Dict[str, str]:
        """Generate multiple diagram types"""
        
        logger.info("Generating multiple diagram types...")
        
        # Analyze content first
        analysis = await self.analyze_content_type(transcript_text)
        primary_type = analysis["primary_type"]
        secondary_types = analysis["secondary_types"]
        
        diagrams = {}
        
        # Generate primary diagram
        if "flowchart" in primary_type or "flowchart" in secondary_types:
            try:
                diagrams["flowchart"] = await self.generate_flowchart(transcript_text, video_title or "Trading System")
            except Exception as e:
                logger.error(f"Flowchart generation failed: {e}")
        
        if "mindmap" in primary_type or "mindmap" in secondary_types:
            try:
                diagrams["mindmap"] = await self.generate_mindmap(transcript_text, video_title or "Trading Concepts")
            except Exception as e:
                logger.error(f"Mindmap generation failed: {e}")
        
        if "timeline" in primary_type or "timeline" in secondary_types:
            try:
                diagrams["timeline"] = await self.generate_timeline(transcript_text, video_title or "Trading Timeline")
            except Exception as e:
                logger.error(f"Timeline generation failed: {e}")
        
        if "sequence" in primary_type or "sequence" in secondary_types:
            try:
                diagrams["sequence"] = await self.generate_sequence(transcript_text, video_title or "Trading Flow")
            except Exception as e:
                logger.error(f"Sequence diagram generation failed: {e}")
        
        # If no diagrams generated, create a basic one
        if not diagrams:
            diagrams["flowchart"] = await self.generate_flowchart(transcript_text, video_title or "Trading Analysis")
        
        return {
            "diagrams": diagrams,
            "analysis": analysis,
            "recommended": primary_type
        }
