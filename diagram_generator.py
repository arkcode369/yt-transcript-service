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
        CRITICAL: This is a TRADING EDUCATION video. EVERY concept, rule, and principle taught is IMPORTANT and must be captured.
        
        Analyze this trading video transcript and determine the best diagram types to represent ALL content.
        
        Available diagram types:
        - flowchart: For trading systems, decision processes, entry/exit rules (MUST capture ALL rules explicitly)
        - mindmap: For trading concepts, strategies, knowledge structures (ALL concepts are important)
        - timeline: For daily/weekly reviews, trading schedules, event sequences
        - sequence: For trade execution flows, system interactions
        
        CRITICAL TRADING PRINCIPLES:
        1. ALL mentor teachings are KEY - do not skip any concept
        2. RULE-BASED content must be extracted with EXPLICIT clarity (e.g., "if X then Y", "always do Z")
        3. Trading requires DISCIPLINE - rules must be clear and actionable
        4. Every strategy component, risk rule, and psychological principle matters
        
        Transcript:
        {transcript_text}
        
        Return JSON format:
        {{
            "primary_type": "flowchart|mindmap|timeline|sequence",
            "secondary_types": ["mindmap", "timeline"],
            "confidence": 0.95,
            "reasoning": "Brief explanation",
            "key_rules_found": ["list", "of", "explicit", "rules"],
            "key_concepts": ["list", "of", "important", "concepts"]
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
                        "max_tokens": 0,  # No limit - let model output all needed content
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
        CRITICAL: This is a TRADING SYSTEM. You MUST extract and represent EVERY rule, condition, and decision point explicitly.
        
        Create a Mermaid.js flowchart from this trading video transcript.
        
        FOCUS ON:
        1. EXPLICIT RULES: Every "if X then Y", "always do Z", "never do W" must be captured
        2. DECISION POINTS: All yes/no questions in the trading process
        3. ENTRY/EXIT RULES: Exact conditions for opening and closing trades
        4. RISK MANAGEMENT: Position sizing rules, stop loss rules, take profit rules
        5. DISCIPLINE RULES: What to do, what NOT to do
        
        Format: Pure Mermaid.js code only, no markdown formatting.
        
        IMPORTANT: Trading requires DISCIPLINE. Every rule taught by the mentor is KEY and must be in the flowchart.
        Do NOT skip any concept or rule - ALL are important for trading success.
        
        Transcript:
        {transcript_text}
        
        Generate flowchart with:
        - Start/End nodes (rounded rectangles)
        - Decision points (diamonds) with EXPLICIT conditions
        - Process steps (rectangles) with CLEAR actions
        - All rules must be visible and actionable
        - Use trading terminology correctly
        
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
        CRITICAL: This is TRADING EDUCATION. EVERY concept taught by the mentor is IMPORTANT and must be included.
        
        Create a Mermaid.js mindmap from this trading video transcript.
        
        REQUIREMENTS:
        1. Capture ALL trading concepts, strategies, and principles
        2. Show relationships between concepts clearly
        3. Include: technical analysis, risk management, psychology, strategy rules
        4. NO concept should be omitted - all are crucial for trading success
        5. Structure hierarchically: Main concepts → Sub-concepts → Details
        
        Format: Pure Mermaid.js code only.
        
        Transcript:
        {transcript_text}
        
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
        
        EXTRACT:
        1. All trading sessions and times
        2. Every trade taken (entry time, exit time, result)
        3. Key events and decisions
        4. Review points and lessons learned
        
        Format: Pure Mermaid.js code only.
        
        Transcript:
        {transcript_text}
        
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
                        "max_tokens": 0,  # No limit - full diagram code
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
