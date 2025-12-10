"""
Email Parser for EML files
Extracts headers, body, and attachments from email files
Adapted from RAGFlow's email.py
"""

import io
import logging
from email import policy
from email.parser import BytesParser
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class EmailParser:
    """Parser for email files (EML format)"""

    SUPPORTED_FORMATS = {
        "message/rfc822",
        "application/vnd.ms-outlook",
        "text/x-email",
    }

    def can_parse(self, content_type: str) -> bool:
        """Check if this parser can handle the content type"""
        if not content_type:
            return False
        return content_type in self.SUPPORTED_FORMATS

    def _decode_payload(self, payload: bytes, charset: str) -> str:
        """Decode email payload with fallback encodings"""
        encodings = [charset, 'utf-8', 'gb2312', 'gbk', 'gb18030', 'latin1']

        for enc in encodings:
            if not enc:
                continue
            try:
                return payload.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue

        return payload.decode('utf-8', errors='ignore')

    def _extract_headers(self, msg) -> Dict[str, str]:
        """Extract email headers as dictionary"""
        headers = {}
        important_headers = [
            'From', 'To', 'Cc', 'Bcc', 'Subject', 'Date',
            'Reply-To', 'Message-ID', 'In-Reply-To', 'References'
        ]

        for header in important_headers:
            value = msg.get(header)
            if value:
                headers[header.lower()] = str(value)

        return headers

    def _strip_html(self, html: str) -> str:
        """Simple HTML tag stripping"""
        import re
        # Remove script and style elements
        text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        return text.strip()

    def _extract_content(
        self,
        msg,
        text_parts: List[str],
        html_parts: List[str]
    ) -> None:
        """
        Recursively extract text and HTML content from message parts

        Args:
            msg: Email message or part
            text_parts: Accumulator for plain text content
            html_parts: Accumulator for HTML content
        """
        content_type = msg.get_content_type()

        if content_type == "text/plain":
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                text_parts.append(self._decode_payload(payload, charset))

        elif content_type == "text/html":
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                html_content = self._decode_payload(payload, charset)
                html_parts.append(self._strip_html(html_content))

        elif content_type.startswith("multipart"):
            if msg.is_multipart():
                for part in msg.iter_parts():
                    self._extract_content(part, text_parts, html_parts)

    def _extract_attachments(self, msg) -> List[Dict[str, Any]]:
        """Extract attachment metadata and content from email"""
        attachments = []

        try:
            for part in msg.iter_attachments():
                content_disposition = part.get("Content-Disposition", "")
                if "attachment" in content_disposition.lower():
                    filename = part.get_filename()
                    content_type = part.get_content_type()
                    payload = part.get_payload(decode=True) or b""
                    size = len(payload)

                    attachment_info = {
                        "filename": filename,
                        "content_type": content_type,
                        "size": size,
                        "payload": payload,  # Store for potential parsing
                    }
                    attachments.append(attachment_info)
        except Exception as e:
            logger.debug(f"Error extracting attachments: {e}")

        return attachments

    async def _parse_attachment(self, attachment: Dict[str, Any]) -> Optional[str]:
        """
        Parse attachment content using appropriate parser

        Args:
            attachment: Attachment dict with filename, content_type, payload

        Returns:
            Parsed content as string or None if parsing fails
        """
        try:
            # Lazy import to avoid circular dependency
            from backend.parsers import ParserFactory

            factory = ParserFactory()
            content_type = attachment.get("content_type", "")
            filename = attachment.get("filename", "attachment")
            payload = attachment.get("payload", b"")

            if not payload:
                return None

            # Try to get appropriate parser
            try:
                parser = factory.get_parser(content_type)
            except ValueError:
                # No parser for this content type
                logger.debug(f"No parser for attachment: {filename} ({content_type})")
                return None

            # Write payload to temp file for parsing
            import tempfile
            import os

            # Get extension from filename
            _, ext = os.path.splitext(filename)
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(payload)
                tmp_path = tmp.name

            try:
                result = await parser.parse(tmp_path)
                return result.get("content", "")
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            logger.debug(f"Failed to parse attachment {attachment.get('filename')}: {e}")
            return None

    def _format_headers_text(self, headers: Dict[str, str]) -> str:
        """Format headers as readable text"""
        lines = []
        order = ['from', 'to', 'cc', 'subject', 'date']

        for key in order:
            if key in headers:
                lines.append(f"{key.title()}: {headers[key]}")

        # Add remaining headers
        for key, value in headers.items():
            if key not in order:
                lines.append(f"{key.title()}: {value}")

        return "\n".join(lines)

    async def parse(
        self,
        file_path: str,
        parse_attachments: bool = True
    ) -> Dict[str, Any]:
        """
        Parse email file and extract headers, body, and attachment info

        Args:
            file_path: Path to EML file
            parse_attachments: Whether to recursively parse attachments

        Returns:
            Dict with:
                - content: Email headers, body, and attachment content
                - metadata: Structured email metadata
                - page_count: 1 (emails are single documents)
        """
        # Read and parse email
        with open(file_path, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)

        # Extract headers
        headers = self._extract_headers(msg)

        # Extract body content
        text_parts = []
        html_parts = []
        self._extract_content(msg, text_parts, html_parts)

        # Extract attachment info
        attachments = self._extract_attachments(msg)

        # Build content string
        content_parts = []

        # Add headers section
        content_parts.append("## Email Headers")
        content_parts.append(self._format_headers_text(headers))
        content_parts.append("")

        # Add body section
        content_parts.append("## Email Body")

        # Prefer plain text, fall back to stripped HTML
        body_text = "\n".join(text_parts) if text_parts else "\n".join(html_parts)
        if body_text:
            content_parts.append(body_text)
        else:
            content_parts.append("(No text content)")

        content_parts.append("")

        # Add attachments section if present
        if attachments:
            content_parts.append("## Attachments")
            parsed_attachments = []
            for att in attachments:
                size_kb = att['size'] / 1024
                content_parts.append(
                    f"- {att['filename']} ({att['content_type']}, {size_kb:.1f} KB)"
                )

                # Try to parse attachment content
                if parse_attachments:
                    parsed_content = await self._parse_attachment(att)
                    if parsed_content:
                        content_parts.append(f"\n### Attachment: {att['filename']}")
                        content_parts.append(parsed_content)
                        content_parts.append("")
                        parsed_attachments.append(att['filename'])

            # Update metadata with parsing info
            if parsed_attachments:
                logger.info(f"Parsed {len(parsed_attachments)} attachments")

        content = "\n".join(content_parts)

        # Remove payload from metadata (too large to store)
        attachments_meta = [
            {k: v for k, v in att.items() if k != 'payload'}
            for att in attachments
        ]

        metadata = {
            "headers": headers,
            "has_attachments": bool(attachments),
            "attachment_count": len(attachments),
            "attachments": attachments_meta,
            "has_html": bool(html_parts),
            "has_plain_text": bool(text_parts),
        }

        return {
            "content": content,
            "metadata": metadata,
            "page_count": 1,
        }
