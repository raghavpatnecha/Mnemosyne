"""
Prompt Builder - Configurable prompt construction with preset support
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.config import CHAT_PRESETS
from backend.prompts.citation import CitationFormatter


class PromptBuilder:
    """
    Builds prompts from Jinja2 templates with citation formatting.

    Supports multiple preset styles:
    - concise: Brief answers with inline citations
    - detailed: Comprehensive with academic citations
    - research: Academic style with full bibliography
    - technical: Precise, detail-oriented with inline citations
    - creative: Exploratory with narrative citations
    """

    def __init__(self):
        # Load templates from templates directory
        templates_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.citation_formatter = CitationFormatter()

        # Map prompt styles to template files
        self.style_templates = {
            "brief": "system_brief.jinja2",
            "comprehensive": "system_comprehensive.jinja2",
            "academic": "system_academic.jinja2",
            "technical": "system_technical.jinja2",
            "exploratory": "system_exploratory.jinja2",
            "qna": "system_qna.jinja2",
        }

    def build_system_prompt(
        self,
        query: str,
        chunks: List[Any],  # ChunkResult objects
        preset: str = "detailed",
        graph_context: Optional[str] = None,
        custom_system_prompt: Optional[str] = None,
        custom_instruction: Optional[str] = None,
        is_follow_up: bool = False,
        previous_context: Optional[str] = None,
    ) -> str:
        """
        Build the system prompt for chat.

        Args:
            query: User's question
            chunks: Retrieved chunks with scores
            preset: Preset name (concise, detailed, research, technical, creative, qna)
            graph_context: Optional LightRAG graph context
            custom_system_prompt: Optional user-provided system prompt override
            custom_instruction: Optional custom instruction to append to prompt
            is_follow_up: Whether this is a follow-up question
            previous_context: Previous context to include for follow-up questions

        Returns:
            Complete system prompt string
        """
        # If custom system prompt provided, use it directly
        if custom_system_prompt:
            context_text, references = self.citation_formatter.format_context_with_citations(
                chunks, style="inline"
            )
            return f"{custom_system_prompt}\n\nContext:\n{context_text}"

        # Get preset configuration
        preset_config = CHAT_PRESETS.get(preset, CHAT_PRESETS["detailed"])
        prompt_style = preset_config.get("system_prompt_style", "comprehensive")
        citation_style = preset_config.get("citation_style", "academic")

        # Format context with citations (chunks only - graph_context handled separately in templates)
        context_text, references = self.citation_formatter.format_context_with_citations(
            chunks, style=citation_style
        )

        # Note: graph_context is passed separately to templates where it appears FIRST
        # before the chunk context, as it contains synthesized answers from LightRAG

        # Get template
        template_name = self.style_templates.get(prompt_style, "system_comprehensive.jinja2")

        try:
            template = self.env.get_template(template_name)
            # Get current date for temporal context
            current_date = datetime.now().strftime("%B %d, %Y")
            rendered = template.render(
                query=query,
                context=context_text,
                references=references,
                graph_context=graph_context,
                current_date=current_date,
                custom_instruction=custom_instruction,
                is_follow_up=is_follow_up,
                previous_context=previous_context,
            )
            return rendered
        except Exception as e:
            # Fallback to basic prompt if template fails
            return self._fallback_prompt(query, context_text, references)

    def _fallback_prompt(
        self,
        query: str,
        context: str,
        references: str,
    ) -> str:
        """Fallback prompt if template loading fails."""
        return f"""You are a helpful assistant. Answer questions using the provided context.
Use [1], [2] style citations when referencing information.

## Context
{context}

## References
{references}

## Question
{query}"""

    def get_preset_config(self, preset: str) -> Dict[str, Any]:
        """Get configuration for a preset."""
        return CHAT_PRESETS.get(preset, CHAT_PRESETS["detailed"])
