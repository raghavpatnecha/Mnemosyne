"""
Table Document Processor.

Enhances table structure recognition from Docling output:
- Parse markdown tables into structured format
- Identify header rows vs data rows (including multi-level headers)
- Detect column types (numeric, date, text, boolean, currency)
- Handle merged cells and spanning headers
- Store structured JSON alongside markdown
- ONNX-based table structure recognition (optional)
- Runtime type conversion for column values

Ported from RAGFlow's table.py with production-tested patterns.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.processors.base import DomainProcessor, ProcessorResult
from backend.processors.ragflow_utils import column_data_type

logger = logging.getLogger(__name__)

# ONNX table structure recognition is loaded lazily to avoid crashes
# on systems where ONNX runtime has issues (e.g., some Windows configurations)
_onnx_module_loaded = False
_TableStructureRecognizer = None
_ONNX_AVAILABLE = False


def _load_onnx_modules():
    """Lazy load ONNX modules. Returns (TableStructureRecognizer, ONNX_AVAILABLE)."""
    global _onnx_module_loaded, _TableStructureRecognizer, _ONNX_AVAILABLE

    if _onnx_module_loaded:
        return _TableStructureRecognizer, _ONNX_AVAILABLE

    _onnx_module_loaded = True

    try:
        from backend.vision import TableStructureRecognizer, ONNX_AVAILABLE
        _TableStructureRecognizer = TableStructureRecognizer
        _ONNX_AVAILABLE = ONNX_AVAILABLE
        logger.debug("ONNX modules loaded successfully")
    except Exception as e:
        logger.warning("Failed to load ONNX modules: %s - ONNX features disabled", e)
        _TableStructureRecognizer = None
        _ONNX_AVAILABLE = False

    return _TableStructureRecognizer, _ONNX_AVAILABLE


# RAGFlow-ported block type patterns for cell classification
BLOCK_TYPE_PATTERNS = [
    # Date patterns
    (r"^(20|19)[0-9]{2}[年/-][0-9]{1,2}[月/-][0-9]{1,2}日*$", "date"),
    (r"^(20|19)[0-9]{2}年$", "date"),
    (r"^(20|19)[0-9]{2}[年-][0-9]{1,2}月*$", "date"),
    (r"^[0-9]{1,2}[月-][0-9]{1,2}日*$", "date"),
    (r"^Q[1-4]\s*(20|19)?[0-9]{2}$", "date"),  # Q1 2024
    (r"^(20|19)[0-9]{2}[ABCDE]$", "date"),
    # Numeric patterns
    (r"^[0-9.,+%/ -]+$", "numeric"),
    (r"^-?\d+\.?\d*$", "numeric"),
    (r"^-?\d{1,3}(,\d{3})*(\.\d+)?$", "numeric"),
    # Code/ID patterns
    (r"^[0-9A-Z/\._~-]+$", "code"),
    # English text
    (r"^[A-Z]*[a-z' -]+$", "text_en"),
    # Mixed numeric-text
    (r"^[0-9.,+-]+[0-9A-Za-z/$%<>()' -]+$", "mixed"),
    # Single character
    (r"^.{1}$", "single"),
]


def _classify_cell_type(text: str) -> str:
    """Classify cell content type using RAGFlow patterns.

    Ported from RAGFlow's TableStructureRecognizer.blockType()

    Args:
        text: Cell text content

    Returns:
        Type classification string
    """
    text = text.strip()
    if not text:
        return "empty"

    for pattern, type_name in BLOCK_TYPE_PATTERNS:
        if re.search(pattern, text):
            return type_name

    # Check token count for text classification
    words = text.split()
    if len(words) > 3:
        return "long_text" if len(words) >= 12 else "text"

    return "other"


def _looks_like_header(value: str) -> bool:
    """Determine if a cell value looks like a header.

    Ported from RAGFlow's Excel._looks_like_header()

    Args:
        value: Cell value to check

    Returns:
        True if value looks like a header
    """
    if len(value) < 1:
        return False

    # Contains non-ASCII characters (likely descriptive text)
    if any(ord(c) > 127 for c in value):
        return True

    # Contains multiple letters (likely a label)
    if len([c for c in value if c.isalpha()]) >= 2:
        return True

    # Contains formatting characters typical of headers
    if any(c in value for c in ["(", ")", ":", "/", "_", "-"]):
        return True

    return False


def _looks_like_data(value: str) -> bool:
    """Determine if a cell value looks like data (not a header).

    Ported from RAGFlow's Excel._looks_like_data()

    Args:
        value: Cell value to check

    Returns:
        True if value looks like data
    """
    # Single character codes
    if len(value) == 1 and value.upper() in ["Y", "N", "M", "X", "/", "-"]:
        return True

    # Numeric values
    if value.replace(".", "").replace("-", "").replace(",", "").isdigit():
        return True

    # Hex codes
    if value.startswith("0x") and len(value) <= 10:
        return True

    return False


class TableProcessor(DomainProcessor):
    """Processor for tabular data documents.

    Enhances table structure recognition by parsing markdown tables
    and extracting semantic information about headers, columns, and data types.
    Optionally uses ONNX-based table structure recognition for image tables.
    """

    name = "table"
    supported_content_types = [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
        "application/pdf",
        "text/plain",
        "text/markdown",
    ]

    def __init__(
        self,
        use_onnx: bool = True,
        model_dir: Optional[str] = None,
    ):
        """Initialize the table processor.

        Args:
            use_onnx: Whether to use ONNX table structure recognition
            model_dir: Directory containing ONNX models
        """
        self._recognizer = None
        self._onnx_enabled = False

        if use_onnx:
            # Lazy load ONNX modules to avoid crashes on problematic systems
            TableStructureRecognizer, ONNX_AVAILABLE = _load_onnx_modules()

            if ONNX_AVAILABLE and TableStructureRecognizer:
                try:
                    self._recognizer = TableStructureRecognizer(model_dir)
                    if self._recognizer.session is not None:
                        self._onnx_enabled = True
                        logger.info("ONNX table structure recognizer enabled")
                    else:
                        logger.warning(
                            "ONNX model not loaded - using markdown parsing only"
                        )
                except Exception as e:
                    logger.warning("Failed to initialize ONNX recognizer: %s", e)

    # Table document indicators
    TABLE_INDICATORS = [
        r"\|[^|]+\|",  # Markdown table rows
        r"^\s*\|[-:]+\|",  # Table separator rows
        r"\b(?:row|column|cell|header|table)\b",
        r"\b(?:spreadsheet|worksheet|excel|csv)\b",
        r"\b(?:total|subtotal|sum|average|count)\b",
        r"\b(?:qty|quantity|amount|price|cost|revenue)\b",
    ]

    # Column type patterns
    COLUMN_TYPE_PATTERNS = {
        "numeric": [
            r"^-?\d+\.?\d*$",
            r"^-?\d{1,3}(,\d{3})*(\.\d+)?$",
            r"^\$?\d+\.?\d*$",
            r"^[\d.]+%$",
        ],
        "date": [
            r"^\d{4}-\d{2}-\d{2}$",
            r"^\d{2}/\d{2}/\d{4}$",
            r"^\d{2}-\d{2}-\d{4}$",
            r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}$",
        ],
        "boolean": [
            r"^(?:true|false|yes|no|y|n|1|0)$",
        ],
        "currency": [
            r"^\$[\d,]+\.?\d*$",
            r"^[\d,]+\.?\d*\s*(?:USD|EUR|GBP|JPY)$",
            r"^(?:USD|EUR|GBP|JPY)\s*[\d,]+\.?\d*$",
        ],
        "percentage": [
            r"^[\d.]+\s*%$",
            r"^[\d.]+\s*percent$",
        ],
    }

    async def process(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
    ) -> ProcessorResult:
        """Process tabular document and extract structure.

        Args:
            content: Document text content (markdown from parser)
            metadata: User-provided metadata
            filename: Original filename

        Returns:
            ProcessorResult with extracted table structure
        """
        logger.debug("Processing table document: %s", filename)

        # Extract all tables from content
        tables = self._extract_markdown_tables(content)

        # Parse each table into structured format
        structured_tables = []
        for i, table_md in enumerate(tables):
            parsed = self._parse_markdown_table(table_md)
            if parsed["headers"] or parsed["rows"]:
                parsed["table_index"] = i
                parsed["column_types"] = self._infer_column_types(parsed)
                parsed["statistics"] = self._calculate_statistics(parsed)
                structured_tables.append(parsed)

        # Generate chunk annotations
        chunk_annotations = self._generate_table_annotations(
            structured_tables, content
        )

        # Prepare table summaries for metadata
        table_summaries = [
            {
                "index": t["table_index"],
                "headers": t["headers"][:10],  # Limit headers
                "row_count": len(t["rows"]),
                "column_count": len(t["headers"]),
                "column_types": t["column_types"],
                "has_header": t["has_header"],
            }
            for t in structured_tables
        ]

        document_metadata = {
            "document_type": "table",
            "table_count": len(structured_tables),
            "tables": table_summaries,
            "total_rows": sum(len(t["rows"]) for t in structured_tables),
            "total_columns": sum(len(t["headers"]) for t in structured_tables),
        }

        return ProcessorResult(
            content=content,
            document_metadata=document_metadata,
            chunk_annotations=chunk_annotations,
            processor_name=self.name,
            confidence=0.95,
        )

    def can_process(self, content: str, metadata: Dict[str, Any]) -> float:
        """Determine if this processor can handle the document.

        Args:
            content: Document text content
            metadata: User-provided metadata

        Returns:
            Confidence score (0-1)
        """
        if not content:
            return 0.0

        sample = content[:15000]
        score = 0.0

        # Check for table indicators
        for pattern in self.TABLE_INDICATORS:
            matches = len(re.findall(pattern, sample, re.IGNORECASE | re.MULTILINE))
            score += min(matches * 0.03, 0.25)

        # Check for markdown table structure
        table_rows = len(re.findall(r"^\s*\|.+\|", sample, re.MULTILINE))
        separator_rows = len(re.findall(r"^\s*\|[-:| ]+\|", sample, re.MULTILINE))

        if table_rows > 2 and separator_rows > 0:
            score += min(table_rows * 0.02, 0.3)
            score += 0.2  # Bonus for having separator rows

        # Check content type from metadata
        content_type = metadata.get("content_type", "")
        if any(
            ct in content_type
            for ct in ["spreadsheet", "excel", "csv"]
        ):
            score += 0.3

        # Check filename
        if filename := metadata.get("filename", ""):
            table_filename_patterns = [
                r"\.xlsx?$",
                r"\.csv$",
                r"data",
                r"report",
                r"spreadsheet",
                r"table",
            ]
            for pattern in table_filename_patterns:
                if re.search(pattern, filename.lower()):
                    score += 0.15
                    break

        return min(score, 1.0)

    def _extract_markdown_tables(self, content: str) -> List[str]:
        """Extract markdown tables from content.

        Args:
            content: Document content

        Returns:
            List of markdown table strings
        """
        tables = []
        lines = content.split("\n")

        current_table_lines = []
        in_table = False

        for line in lines:
            # Check if line is a table row (contains | characters)
            is_table_row = bool(re.match(r"^\s*\|.+\|", line))

            if is_table_row:
                current_table_lines.append(line)
                in_table = True
            else:
                if in_table and current_table_lines:
                    # End of table
                    table_content = "\n".join(current_table_lines)
                    # Only keep tables with at least header + separator + 1 data row
                    if len(current_table_lines) >= 3:
                        tables.append(table_content)
                    current_table_lines = []
                in_table = False

        # Don't forget the last table
        if current_table_lines and len(current_table_lines) >= 3:
            tables.append("\n".join(current_table_lines))

        return tables

    def _parse_markdown_table(self, table_md: str) -> Dict[str, Any]:
        """Parse markdown table into structured format.

        Uses RAGFlow-ported logic for multi-level header detection.

        Args:
            table_md: Markdown table string

        Returns:
            Dictionary with headers, rows, and metadata
        """
        lines = [line.strip() for line in table_md.strip().split("\n") if line.strip()]

        if not lines:
            return {"headers": [], "rows": [], "has_header": False}

        # Parse all rows first
        all_rows = [self._parse_table_row(line) for line in lines]

        # Detect header rows using RAGFlow logic
        header_rows, data_start = self._detect_header_rows(all_rows, lines)

        if header_rows > 0:
            # Build hierarchical headers
            headers = self._build_hierarchical_headers(all_rows[:header_rows])
            has_header = True
        else:
            # No header detected - use first row as data
            headers = [f"Column_{i+1}" for i in range(len(all_rows[0]) if all_rows else 0)]
            data_start = 0
            has_header = False

        # Parse data rows
        rows = []
        for i in range(data_start, len(all_rows)):
            # Skip separator rows
            if re.match(r"^\s*\|[-:\s|]+\|", lines[i]):
                continue

            cells = all_rows[i]
            if cells:
                # Create row dict mapping headers to values
                row = {}
                for j, cell in enumerate(cells):
                    header = headers[j] if j < len(headers) else f"Column_{j+1}"
                    row[header] = cell
                rows.append(row)

        return {
            "headers": headers,
            "rows": rows,
            "has_header": has_header,
            "header_rows": header_rows,
            "raw_markdown": table_md,
        }

    def _detect_header_rows(
        self, all_rows: List[List[str]], lines: List[str]
    ) -> Tuple[int, int]:
        """Detect how many rows are headers using RAGFlow logic.

        Ported from RAGFlow's Excel._detect_header_rows()

        Args:
            all_rows: List of parsed row cells
            lines: Original line strings

        Returns:
            Tuple of (header_row_count, data_start_index)
        """
        if not all_rows:
            return 0, 0

        # Check for markdown separator (|---|---|)
        for i, line in enumerate(lines):
            if re.match(r"^\s*\|[-:\s|]+\|", line):
                # Separator found - everything before is header
                return i, i + 1

        # No separator - use heuristics
        header_rows = 0
        max_check = min(5, len(all_rows))

        for i in range(max_check):
            row = all_rows[i]
            if self._row_looks_like_header(row):
                header_rows = i + 1
            else:
                break

        # If we found headers, data starts after them
        data_start = header_rows if header_rows > 0 else 0
        return header_rows, data_start

    def _row_looks_like_header(self, row: List[str]) -> bool:
        """Determine if a row looks like a header row.

        Ported from RAGFlow's Excel._row_looks_like_header()

        Args:
            row: List of cell values

        Returns:
            True if row looks like a header
        """
        header_like_cells = 0
        data_like_cells = 0
        non_empty_cells = 0

        for cell in row:
            if cell and cell.strip():
                non_empty_cells += 1
                val = cell.strip()

                if _looks_like_header(val):
                    header_like_cells += 1
                elif _looks_like_data(val):
                    data_like_cells += 1

        if non_empty_cells == 0:
            return False

        return header_like_cells >= data_like_cells

    def _build_hierarchical_headers(
        self, header_rows: List[List[str]]
    ) -> List[str]:
        """Build hierarchical headers from multiple header rows.

        Ported from RAGFlow's Excel._build_hierarchical_headers()

        Args:
            header_rows: List of header row cells

        Returns:
            List of combined header strings
        """
        if not header_rows:
            return []

        if len(header_rows) == 1:
            return [cell.strip() if cell else f"Column_{i+1}"
                    for i, cell in enumerate(header_rows[0])]

        # Multiple header rows - combine them
        max_cols = max(len(row) for row in header_rows)
        headers = []

        for col_idx in range(max_cols):
            header_parts = []

            for row in header_rows:
                if col_idx < len(row):
                    cell_value = row[col_idx]
                    if cell_value and cell_value.strip():
                        cell_value = cell_value.strip()
                        # Don't duplicate parts
                        if cell_value not in header_parts:
                            # Filter out data-like values
                            if not _looks_like_data(cell_value):
                                header_parts.append(cell_value)

            if header_parts:
                # Join with delimiter for hierarchical header
                header = " - ".join(header_parts)
                headers.append(header)
            else:
                headers.append(f"Column_{col_idx + 1}")

        return headers

    def _parse_table_row(self, row: str) -> List[str]:
        """Parse a single table row into cells.

        Args:
            row: Table row string

        Returns:
            List of cell values
        """
        # Remove leading/trailing pipes and split
        row = row.strip()
        if row.startswith("|"):
            row = row[1:]
        if row.endswith("|"):
            row = row[:-1]

        # Split by pipe and clean cells
        cells = [cell.strip() for cell in row.split("|")]

        # Filter out empty cells from malformed rows
        # But keep empty strings that are between valid cells
        return cells

    def _infer_column_types(self, parsed_table: Dict[str, Any]) -> Dict[str, str]:
        """Infer data types for each column using RAGFlow's column_data_type().

        Uses RAGFlow's runtime type inference and conversion algorithm
        for more accurate type detection and value conversion.

        Args:
            parsed_table: Parsed table dictionary

        Returns:
            Dictionary mapping column names to inferred types
        """
        column_types = {}
        headers = parsed_table.get("headers", [])
        rows = parsed_table.get("rows", [])

        if not rows:
            return {h: "text" for h in headers}

        for header in headers:
            # Collect values for this column (including None for empty)
            values = [row.get(header, "") for row in rows]

            if not any(v.strip() if isinstance(v, str) else v for v in values):
                column_types[header] = "text"
                continue

            # Use RAGFlow's column_data_type for runtime type inference
            converted_values, detected_type = column_data_type(values)

            # Update rows with converted values
            for i, row in enumerate(rows):
                if header in row and i < len(converted_values):
                    # Store converted value back to row
                    row[f"{header}_converted"] = converted_values[i]

            # Map RAGFlow types to our type names
            type_mapping = {
                "int": "numeric",
                "float": "numeric",
                "datetime": "date",
                "bool": "boolean",
                "text": "text",
            }
            column_types[header] = type_mapping.get(detected_type, "text")

        return column_types

    def _infer_column_types_legacy(
        self, parsed_table: Dict[str, Any]
    ) -> Dict[str, str]:
        """Legacy type inference using pattern matching (fallback).

        Args:
            parsed_table: Parsed table dictionary

        Returns:
            Dictionary mapping column names to inferred types
        """
        column_types = {}
        headers = parsed_table.get("headers", [])
        rows = parsed_table.get("rows", [])

        if not rows:
            return {h: "text" for h in headers}

        for header in headers:
            # Collect non-empty values for this column
            values = [
                row.get(header, "")
                for row in rows
                if row.get(header, "").strip()
            ]

            if not values:
                column_types[header] = "text"
                continue

            # Check each type pattern
            type_scores = {t: 0 for t in self.COLUMN_TYPE_PATTERNS}

            for value in values:
                value = value.strip()
                for type_name, patterns in self.COLUMN_TYPE_PATTERNS.items():
                    for pattern in patterns:
                        if re.match(pattern, value, re.IGNORECASE):
                            type_scores[type_name] += 1
                            break

            # Get best matching type (majority wins)
            best_type = "text"
            best_score = 0
            threshold = len(values) * 0.5  # Need 50% match

            for type_name, score in type_scores.items():
                if score > best_score and score >= threshold:
                    best_score = score
                    best_type = type_name

            column_types[header] = best_type

        return column_types

    def _calculate_statistics(self, parsed_table: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate basic statistics for numeric columns.

        Args:
            parsed_table: Parsed table dictionary

        Returns:
            Statistics dictionary
        """
        stats = {}
        column_types = parsed_table.get("column_types", {})
        rows = parsed_table.get("rows", [])

        for header, col_type in column_types.items():
            if col_type in ("numeric", "currency", "percentage"):
                values = []
                for row in rows:
                    value = row.get(header, "")
                    # Clean and parse numeric value
                    cleaned = re.sub(r"[,$%\s]", "", value)
                    try:
                        values.append(float(cleaned))
                    except (ValueError, TypeError):
                        pass

                if values:
                    stats[header] = {
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "count": len(values),
                    }

        return stats

    def _generate_table_annotations(
        self, structured_tables: List[Dict[str, Any]], content: str
    ) -> List[Dict[str, Any]]:
        """Generate chunk annotations for tables.

        Args:
            structured_tables: List of parsed tables
            content: Original content

        Returns:
            List of chunk annotations
        """
        annotations = []

        for table in structured_tables:
            # Find table position in content
            raw_md = table.get("raw_markdown", "")
            position = content.find(raw_md) if raw_md else -1

            annotations.append(
                {
                    "table_index": table["table_index"],
                    "type": "table",
                    "position": position if position >= 0 else None,
                    "headers": table["headers"],
                    "row_count": len(table["rows"]),
                    "column_types": table.get("column_types", {}),
                    "has_header": table["has_header"],
                    "preserve_structure": True,  # Hint to keep table together
                }
            )

        return annotations

    def process_table_image(
        self,
        image: np.ndarray,
        threshold: float = 0.2,
    ) -> Dict[str, Any]:
        """Process a table image using ONNX structure recognition.

        This method uses the ONNX TableStructureRecognizer to detect
        table structure elements (rows, columns, headers, spanning cells)
        from an image of a table.

        Args:
            image: Table image as numpy array (RGB)
            threshold: Confidence threshold for detections

        Returns:
            Dictionary with detected structure elements:
            - rows: List of row bounding boxes
            - columns: List of column bounding boxes
            - headers: List of header cell detections
            - spanning_cells: List of spanning cell detections
            - table_bbox: Overall table boundary
        """
        if not self._onnx_enabled or self._recognizer is None:
            logger.warning("ONNX recognizer not available")
            return {"rows": [], "columns": [], "headers": [], "spanning_cells": []}

        try:
            # Run recognition
            results = self._recognizer([image], threshold=threshold)

            if not results or not results[0]:
                return {"rows": [], "columns": [], "headers": [], "spanning_cells": []}

            detections = results[0]

            # Categorize detections by type
            structure = {
                "rows": [],
                "columns": [],
                "headers": [],
                "spanning_cells": [],
                "table_bbox": None,
            }

            for det in detections:
                det_type = det.get("type", "")
                bbox = det.get("bbox", [])
                score = det.get("score", 0)

                if "row" in det_type:
                    structure["rows"].append({
                        "bbox": bbox,
                        "score": score,
                        "is_header": "header" in det_type,
                    })
                elif "column" in det_type:
                    structure["columns"].append({
                        "bbox": bbox,
                        "score": score,
                        "is_header": "header" in det_type,
                    })
                elif "spanning" in det_type:
                    structure["spanning_cells"].append({
                        "bbox": bbox,
                        "score": score,
                    })
                elif det_type == "table":
                    structure["table_bbox"] = bbox

                # Track header detections separately
                if "header" in det_type:
                    structure["headers"].append({
                        "bbox": bbox,
                        "score": score,
                        "type": det_type,
                    })

            # Sort rows by Y position, columns by X position
            structure["rows"].sort(key=lambda r: r["bbox"][1] if r["bbox"] else 0)
            structure["columns"].sort(key=lambda c: c["bbox"][0] if c["bbox"] else 0)

            return structure

        except Exception as e:
            logger.error("ONNX table recognition failed: %s", e)
            return {"rows": [], "columns": [], "headers": [], "spanning_cells": []}

    def construct_table_from_structure(
        self,
        structure: Dict[str, Any],
        text_boxes: List[Dict[str, Any]],
        as_html: bool = True,
    ) -> str:
        """Construct table from ONNX structure and text boxes.

        Combines ONNX-detected structure with OCR text boxes
        to build a complete table representation.

        Args:
            structure: Structure from process_table_image()
            text_boxes: List of text boxes with 'text', 'bbox' keys
            as_html: Return HTML format (vs markdown)

        Returns:
            Table as HTML or markdown string
        """
        if not structure.get("rows") or not structure.get("columns"):
            return ""

        if not self._recognizer:
            return ""

        # Use RAGFlow's construct_table method
        return TableStructureRecognizer.construct_table(
            text_boxes,
            is_english=True,
            as_html=as_html,
        )

    @property
    def onnx_available(self) -> bool:
        """Check if ONNX recognition is available."""
        return self._onnx_enabled

    @classmethod
    def download_onnx_model(cls, model_dir: Optional[str] = None) -> bool:
        """Download the ONNX model for table structure recognition.

        Args:
            model_dir: Directory to save the model

        Returns:
            True if download successful
        """
        TableStructureRecognizer, _ = _load_onnx_modules()

        if not TableStructureRecognizer:
            logger.error("TableStructureRecognizer not available")
            return False

        return TableStructureRecognizer.download_model(model_dir)
