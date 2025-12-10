"""
JSON Parser for JSON and JSONL files
Structure-preserving chunking for JSON data
Adapted from RAGFlow's json_parser.py
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class JSONParser:
    """Parser for JSON and JSONL files"""

    SUPPORTED_FORMATS = {
        "application/json",
        "application/x-jsonlines",
        "application/jsonl",
        "text/json",
    }

    def __init__(self, max_chunk_size: int = 2000, min_chunk_size: int = None):
        """
        Initialize JSON parser

        Args:
            max_chunk_size: Maximum characters per JSON chunk
            min_chunk_size: Minimum characters before starting new chunk
        """
        self.max_chunk_size = max_chunk_size * 2
        self.min_chunk_size = min_chunk_size or max(max_chunk_size - 200, 50)

    def can_parse(self, content_type: str) -> bool:
        """Check if this parser can handle the content type"""
        if not content_type:
            return False
        return content_type in self.SUPPORTED_FORMATS

    def _detect_encoding(self, binary: bytes) -> str:
        """Detect file encoding"""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'gbk', 'gb2312']
        for encoding in encodings:
            try:
                binary.decode(encoding)
                return encoding
            except (UnicodeDecodeError, LookupError):
                continue
        return 'utf-8'

    def _is_jsonl_format(self, text: str, sample_limit: int = 10) -> bool:
        """
        Detect if text is JSONL format (newline-delimited JSON)

        Args:
            text: Text content to analyze
            sample_limit: Number of lines to sample

        Returns:
            True if JSONL format detected
        """
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if not lines:
            return False

        # First try parsing as single JSON object
        try:
            json.loads(text)
            return False  # Valid single JSON, not JSONL
        except json.JSONDecodeError:
            pass

        # Check if lines are individual JSON objects
        sample_lines = lines[:min(len(lines), sample_limit)]
        valid_count = sum(1 for line in sample_lines if self._is_valid_json(line))

        if not valid_count:
            return False

        return (valid_count / len(sample_lines)) >= 0.8

    def _is_valid_json(self, line: str) -> bool:
        """Check if a string is valid JSON"""
        try:
            json.loads(line)
            return True
        except json.JSONDecodeError:
            return False

    @staticmethod
    def _json_size(data: dict) -> int:
        """Calculate serialized JSON size"""
        return len(json.dumps(data, ensure_ascii=False))

    @staticmethod
    def _set_nested_dict(d: dict, path: List[str], value: Any) -> None:
        """Set value in nested dict by path"""
        for key in path[:-1]:
            d = d.setdefault(key, {})
        d[path[-1]] = value

    def _list_to_dict(self, data: Any) -> Any:
        """Convert lists to index-keyed dicts for consistent chunking"""
        if isinstance(data, dict):
            return {k: self._list_to_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return {str(i): self._list_to_dict(item) for i, item in enumerate(data)}
        return data

    def _split_json(
        self,
        data: Any,
        current_path: List[str] = None,
        chunks: List[dict] = None
    ) -> List[dict]:
        """
        Split JSON into chunks while preserving structure

        Args:
            data: JSON data to split
            current_path: Current path in JSON tree
            chunks: Accumulated chunks

        Returns:
            List of JSON chunk dictionaries
        """
        current_path = current_path or []
        chunks = chunks or [{}]

        if isinstance(data, dict):
            for key, value in data.items():
                new_path = current_path + [key]
                chunk_size = self._json_size(chunks[-1])
                item_size = self._json_size({key: value})
                remaining = self.max_chunk_size - chunk_size

                if item_size < remaining:
                    self._set_nested_dict(chunks[-1], new_path, value)
                else:
                    if chunk_size >= self.min_chunk_size:
                        chunks.append({})
                    self._split_json(value, new_path, chunks)
        else:
            self._set_nested_dict(chunks[-1], current_path, data)

        return chunks

    def _parse_json(self, content: str) -> List[str]:
        """Parse standard JSON content"""
        sections = []
        try:
            json_data = json.loads(content)
            converted = self._list_to_dict(json_data)
            chunks = self._split_json(converted)
            sections = [
                json.dumps(chunk, ensure_ascii=False, indent=2)
                for chunk in chunks if chunk
            ]
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
        return sections

    def _parse_jsonl(self, content: str) -> List[str]:
        """Parse JSONL (newline-delimited JSON) content"""
        sections = []
        for line in content.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                converted = self._list_to_dict(data)
                chunks = self._split_json(converted)
                sections.extend(
                    json.dumps(chunk, ensure_ascii=False, indent=2)
                    for chunk in chunks if chunk
                )
            except json.JSONDecodeError:
                continue
        return sections

    def _json_to_text(self, json_str: str) -> str:
        """Convert JSON to readable text format"""
        try:
            data = json.loads(json_str)
            return self._flatten_json(data)
        except json.JSONDecodeError:
            return json_str

    def _flatten_json(self, data: Any, prefix: str = "") -> str:
        """Flatten JSON to key: value text format"""
        lines = []
        if isinstance(data, dict):
            for key, value in data.items():
                new_prefix = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
                if isinstance(value, (dict, list)):
                    lines.append(self._flatten_json(value, new_prefix))
                else:
                    lines.append(f"{new_prefix}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_prefix = f"{prefix}[{i}]"
                lines.append(self._flatten_json(item, new_prefix))
        else:
            return f"{prefix}: {data}" if prefix else str(data)
        return "\n".join(filter(None, lines))

    async def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse JSON or JSONL file

        Args:
            file_path: Path to JSON file

        Returns:
            Dict with:
                - content: Flattened JSON as readable text
                - metadata: Format info, record count
                - page_count: Number of JSON sections
        """
        # Read file
        with open(file_path, "rb") as f:
            binary = f.read()

        encoding = self._detect_encoding(binary)
        text = binary.decode(encoding, errors="ignore")

        # Detect format and parse
        is_jsonl = self._is_jsonl_format(text)

        if is_jsonl:
            sections = self._parse_jsonl(text)
            format_type = "jsonl"
        else:
            sections = self._parse_json(text)
            format_type = "json"

        # Convert JSON sections to readable text
        content_parts = []
        for i, section in enumerate(sections):
            readable = self._json_to_text(section)
            if readable:
                content_parts.append(f"## Section {i + 1}\n{readable}")

        content = "\n\n".join(content_parts)

        metadata = {
            "format": format_type,
            "encoding": encoding,
            "section_count": len(sections),
            "original_size": len(binary),
        }

        return {
            "content": content,
            "metadata": metadata,
            "page_count": len(sections) or 1,
        }
