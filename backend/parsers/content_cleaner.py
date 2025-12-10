"""
Content Cleaner for RAG-optimized document parsing
Removes garbage artifacts from parsed documents that hurt retrieval quality

Problem:
- PDF parsers (Docling) export markdown with table structures like |---|---|
- These artifacts are useless for RAG and pollute chunk embeddings
- Image placeholders like <!-- image --> add no semantic value

Solution:
- Clean content BEFORE chunking for better retrieval quality
- Convert tables to readable text format
- Remove HTML comments and artifacts
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def clean_content_for_rag(content: str) -> str:
    """
    Clean parsed document content for optimal RAG quality

    Removes:
    - Markdown table separators (|---|---|)
    - Empty table cells (| | |)
    - HTML comments (<!-- image -->)
    - Excessive whitespace
    - Redundant newlines

    Converts:
    - Table rows to readable text

    Args:
        content: Raw parsed document content (markdown format)

    Returns:
        Cleaned content optimized for RAG chunking and retrieval
    """
    if not content:
        return content

    original_length = len(content)

    # 1. Remove HTML comments (<!-- image -->, <!-- comment -->, etc.)
    content = re.sub(r'<!--[^>]*-->', '', content)

    # 2. Remove markdown table separator rows (|---|---|---|)
    # Match rows that are ONLY dashes and pipes
    content = re.sub(r'\|[\s\-:]+\|[\s\-:|]*\n?', '\n', content)

    # 3. Convert table rows to readable text
    # |cell1|cell2|cell3| -> cell1, cell2, cell3
    def convert_table_row(match):
        row = match.group(0)
        # Split by pipe and clean
        cells = [cell.strip() for cell in row.split('|') if cell.strip()]
        if not cells:
            return ''
        # Filter out cells that are just dashes
        cells = [c for c in cells if not re.match(r'^[\s\-:]+$', c)]
        if not cells:
            return ''
        return ' | '.join(cells) + '\n'

    # Match table rows (lines starting and ending with |)
    content = re.sub(r'^\|[^\n]+\|$', convert_table_row, content, flags=re.MULTILINE)

    # 4. Remove empty pipe separators (leftover from table cleaning)
    content = re.sub(r'\|\s*\|', '', content)
    content = re.sub(r'^\|\s*$', '', content, flags=re.MULTILINE)

    # 5. Clean up bullet point artifacts
    # Convert weird bullet patterns to clean bullets
    content = re.sub(r'[·•]\s*', '- ', content)
    content = re.sub(r'^\s*-\s*$', '', content, flags=re.MULTILINE)  # Remove empty bullets

    # 6. Remove excessive whitespace
    # Multiple spaces to single space
    content = re.sub(r'[ \t]+', ' ', content)

    # Multiple newlines to max 2
    content = re.sub(r'\n{3,}', '\n\n', content)

    # Remove leading/trailing whitespace on each line
    lines = [line.strip() for line in content.split('\n')]
    content = '\n'.join(lines)

    # 7. Remove lines that are only whitespace or special characters
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        # Skip lines that are only special characters
        if re.match(r'^[\s\-|_*#=]+$', line):
            continue
        cleaned_lines.append(line)
    content = '\n'.join(cleaned_lines)

    # 8. Final cleanup - remove leading/trailing whitespace
    content = content.strip()

    cleaned_length = len(content)
    reduction = original_length - cleaned_length
    if reduction > 100:  # Only log significant reductions
        logger.info(
            f"Content cleaned: {original_length} -> {cleaned_length} chars "
            f"({reduction} chars removed, {reduction/original_length*100:.1f}% reduction)"
        )

    return content


def clean_table_to_text(table_markdown: str) -> str:
    """
    Convert a markdown table to readable text format

    Example:
        Input:  |Name|Age|City|
                |---|---|---|
                |John|25|NYC|

        Output: Name: John, Age: 25, City: NYC
    """
    lines = table_markdown.strip().split('\n')
    if len(lines) < 2:
        return table_markdown

    # Extract headers
    header_line = lines[0]
    headers = [h.strip() for h in header_line.split('|') if h.strip()]

    # Skip separator line (|---|---|)
    data_lines = [l for l in lines[1:] if not re.match(r'^[\s\-|:]+$', l)]

    result_lines = []
    for line in data_lines:
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if len(cells) == len(headers):
            pairs = [f"{h}: {c}" for h, c in zip(headers, cells) if c]
            if pairs:
                result_lines.append(', '.join(pairs))
        elif cells:
            result_lines.append(' '.join(cells))

    return '\n'.join(result_lines)
