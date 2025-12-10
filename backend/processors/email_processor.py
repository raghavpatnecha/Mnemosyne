"""
Email Document Processor.

Extracts metadata and structure from email content including:
- Header parsing (From, To, Subject, Date, etc.)
- Thread detection
- Attachment identification
- Reply chain extraction

Adapted from RAGFlow's email.py processor patterns.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.processors.base import DomainProcessor, ProcessorResult

logger = logging.getLogger(__name__)


class EmailProcessor(DomainProcessor):
    """Processor for email documents.

    Extracts structure and metadata from emails, including
    headers, body, attachments, and thread information.
    """

    name = "email"
    supported_content_types = [
        "message/rfc822",
        "application/vnd.ms-outlook",
        "text/x-email",
        "text/plain",
    ]

    # Email header patterns
    HEADER_PATTERNS = {
        "from": r"^From:\s*(.+)$",
        "to": r"^To:\s*(.+)$",
        "cc": r"^Cc:\s*(.+)$",
        "bcc": r"^Bcc:\s*(.+)$",
        "subject": r"^Subject:\s*(.+)$",
        "date": r"^Date:\s*(.+)$",
        "reply_to": r"^Reply-To:\s*(.+)$",
        "message_id": r"^Message-ID:\s*(.+)$",
        "in_reply_to": r"^In-Reply-To:\s*(.+)$",
        "references": r"^References:\s*(.+)$",
    }

    # Email indicators for detection
    EMAIL_INDICATORS = [
        r"^From:\s*",
        r"^To:\s*",
        r"^Subject:\s*",
        r"^Date:\s*",
        r"^Reply-To:\s*",
        r"^Message-ID:\s*",
        r"@[\w.-]+\.\w+",  # Email addresses
        r"^Sent:\s*",
        r"^Received:\s*",
    ]

    # Reply/forward patterns
    REPLY_PATTERNS = [
        r"^-+\s*Original\s+Message\s*-+",
        r"^On\s+.+wrote:",
        r"^From:\s*.+\nSent:\s*",
        r"^>+\s*",
        r"^Forwarded\s+message",
        r"^Begin\s+forwarded\s+message",
    ]

    # Signature patterns
    SIGNATURE_PATTERNS = [
        r"^--\s*$",
        r"^_{3,}$",
        r"^Best\s+regards?,?\s*$",
        r"^Kind\s+regards?,?\s*$",
        r"^Sincerely,?\s*$",
        r"^Thanks?,?\s*$",
        r"^Cheers,?\s*$",
    ]

    async def process(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
    ) -> ProcessorResult:
        """Process email content and extract structure.

        Args:
            content: Email text content
            metadata: User-provided metadata
            filename: Original filename

        Returns:
            ProcessorResult with extracted email structure
        """
        logger.debug("Processing email document: %s", filename)

        # Extract headers
        headers = self._extract_headers(content)

        # Parse email addresses
        sender = self._parse_email_address(headers.get("from", ""))
        recipients = self._parse_recipients(headers)

        # Extract subject
        subject = headers.get("subject", "")

        # Parse date
        date_str = headers.get("date", "")
        parsed_date = self._parse_date(date_str)

        # Detect thread/reply chain
        thread_info = self._detect_thread(content, headers)

        # Extract body (without headers)
        body = self._extract_body(content)

        # Detect signature
        signature = self._detect_signature(body)

        # Detect attachments (from content markers)
        attachments = self._detect_attachments(content)

        # Generate chunk annotations
        chunk_annotations = self._generate_chunk_annotations(content, headers)

        document_metadata = {
            "document_type": "email",
            "subject": subject,
            "from": sender,
            "to": recipients.get("to", []),
            "cc": recipients.get("cc", []),
            "date": parsed_date,
            "date_raw": date_str,
            "message_id": headers.get("message_id"),
            "is_reply": thread_info.get("is_reply", False),
            "is_forward": thread_info.get("is_forward", False),
            "thread_depth": thread_info.get("depth", 0),
            "has_attachments": len(attachments) > 0,
            "attachment_count": len(attachments),
            "attachments": attachments,
            "has_signature": signature is not None,
            "headers": headers,
        }

        return ProcessorResult(
            content=content,
            document_metadata=document_metadata,
            chunk_annotations=chunk_annotations,
            processor_name=self.name,
            confidence=0.9,
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

        sample = content[:5000]
        score = 0.0

        # Check for email indicators
        for pattern in self.EMAIL_INDICATORS:
            if re.search(pattern, sample, re.MULTILINE | re.IGNORECASE):
                score += 0.15

        # Must have From: and Subject: or To:
        has_from = bool(re.search(r"^From:\s*", sample, re.MULTILINE | re.IGNORECASE))
        has_subject = bool(re.search(r"^Subject:\s*", sample, re.MULTILINE | re.IGNORECASE))
        has_to = bool(re.search(r"^To:\s*", sample, re.MULTILINE | re.IGNORECASE))

        if has_from and (has_subject or has_to):
            score += 0.3

        # Check for email addresses
        email_count = len(re.findall(r"[\w.-]+@[\w.-]+\.\w+", sample))
        score += min(email_count * 0.05, 0.2)

        # Check filename
        if filename := metadata.get("filename", ""):
            if filename.lower().endswith((".eml", ".msg")):
                score += 0.3
            if re.search(r"email|mail|message", filename.lower()):
                score += 0.1

        return min(score, 1.0)

    def _extract_headers(self, content: str) -> Dict[str, str]:
        """Extract email headers from content.

        Args:
            content: Email content

        Returns:
            Dictionary of header values
        """
        headers = {}
        lines = content.split("\n")

        for line in lines[:100]:  # Headers in first 100 lines
            for header_name, pattern in self.HEADER_PATTERNS.items():
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    headers[header_name] = match.group(1).strip()
                    break

            # Stop at blank line (end of headers)
            if not line.strip() and headers:
                break

        return headers

    def _parse_email_address(self, addr_string: str) -> Dict[str, str]:
        """Parse email address string into components.

        Args:
            addr_string: Email address string (e.g., "John Doe <john@example.com>")

        Returns:
            Dictionary with name and email
        """
        if not addr_string:
            return {"name": "", "email": ""}

        # Pattern: Name <email@domain.com>
        match = re.match(r"^(.+?)\s*<([^>]+)>$", addr_string.strip())
        if match:
            return {
                "name": match.group(1).strip().strip('"'),
                "email": match.group(2).strip(),
            }

        # Just email address
        match = re.match(r"^([\w.-]+@[\w.-]+\.\w+)$", addr_string.strip())
        if match:
            return {"name": "", "email": match.group(1)}

        return {"name": addr_string.strip(), "email": ""}

    def _parse_recipients(self, headers: Dict[str, str]) -> Dict[str, List[Dict]]:
        """Parse all recipient fields.

        Args:
            headers: Extracted headers

        Returns:
            Dictionary with to, cc, bcc lists
        """
        recipients = {"to": [], "cc": [], "bcc": []}

        for field in ["to", "cc", "bcc"]:
            if field in headers:
                # Split by comma, handling quoted names
                addr_list = re.split(r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)', headers[field])
                for addr in addr_list:
                    parsed = self._parse_email_address(addr)
                    if parsed.get("email") or parsed.get("name"):
                        recipients[field].append(parsed)

        return recipients

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse email date string.

        Args:
            date_str: Date string from header

        Returns:
            ISO format date string or None
        """
        if not date_str:
            return None

        # Common date formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822
            "%d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S",
            "%d %b %Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ]

        # Clean up date string
        date_str = re.sub(r"\s+\([A-Z]+\)$", "", date_str)  # Remove timezone name
        date_str = date_str.strip()

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat()
            except ValueError:
                continue

        return None

    def _detect_thread(
        self, content: str, headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Detect if email is part of a thread.

        Args:
            content: Email content
            headers: Extracted headers

        Returns:
            Thread information dictionary
        """
        thread_info = {
            "is_reply": False,
            "is_forward": False,
            "depth": 0,
        }

        # Check headers for reply indicators
        if headers.get("in_reply_to") or headers.get("references"):
            thread_info["is_reply"] = True

        # Check subject for Re:/Fwd:
        subject = headers.get("subject", "")
        re_count = len(re.findall(r"^(?:Re|RE|re):\s*", subject))
        fwd_count = len(re.findall(r"^(?:Fwd|FWD|Fw|FW):\s*", subject))

        if re_count > 0:
            thread_info["is_reply"] = True
            thread_info["depth"] = re_count

        if fwd_count > 0:
            thread_info["is_forward"] = True

        # Check content for reply patterns
        for pattern in self.REPLY_PATTERNS:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                thread_info["is_reply"] = True
                break

        # Count quoted lines for depth estimation
        quoted_lines = len(re.findall(r"^>+", content, re.MULTILINE))
        if quoted_lines > 5:
            thread_info["depth"] = max(
                thread_info["depth"],
                min(quoted_lines // 10, 5),
            )

        return thread_info

    def _extract_body(self, content: str) -> str:
        """Extract email body without headers.

        Args:
            content: Full email content

        Returns:
            Body text
        """
        lines = content.split("\n")
        body_start = 0

        # Find end of headers (first blank line after headers)
        in_headers = False
        for i, line in enumerate(lines):
            if re.match(r"^[A-Za-z-]+:\s*", line):
                in_headers = True
            elif in_headers and not line.strip():
                body_start = i + 1
                break

        return "\n".join(lines[body_start:])

    def _detect_signature(self, body: str) -> Optional[str]:
        """Detect email signature.

        Args:
            body: Email body text

        Returns:
            Signature text or None
        """
        lines = body.split("\n")
        signature_start = None

        for i, line in enumerate(lines):
            for pattern in self.SIGNATURE_PATTERNS:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    signature_start = i
                    break

            if signature_start is not None:
                break

        if signature_start is not None:
            signature_lines = lines[signature_start:]
            # Limit signature length
            if len(signature_lines) <= 15:
                return "\n".join(signature_lines)

        return None

    def _detect_attachments(self, content: str) -> List[Dict[str, str]]:
        """Detect attachment information from content.

        Args:
            content: Email content

        Returns:
            List of attachment info dictionaries
        """
        attachments = []

        # Look for attachment markers in content
        attachment_patterns = [
            r"Attachment:\s*(.+?)(?:\s*\(([^)]+)\))?$",
            r"Attached:\s*(.+?)(?:\s*\(([^)]+)\))?$",
            r"File:\s*(.+?)(?:\s*\(([^)]+)\))?$",
            r"-\s*(.+?\.(?:pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar))\s*\(([^)]+)\)",
        ]

        for pattern in attachment_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                filename = match[0].strip() if match[0] else ""
                size = match[1].strip() if len(match) > 1 and match[1] else ""
                if filename:
                    attachments.append({
                        "filename": filename,
                        "size": size,
                    })

        return attachments

    def _generate_chunk_annotations(
        self, content: str, headers: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Generate chunk annotations for email.

        Args:
            content: Email content
            headers: Extracted headers

        Returns:
            List of chunk annotations
        """
        annotations = []
        lines = content.split("\n")

        # Find header section
        header_end = 0
        for i, line in enumerate(lines):
            if not line.strip() and i > 0:
                header_end = i
                break

        # Header annotation
        if header_end > 0:
            header_text = "\n".join(lines[:header_end])
            annotations.append({
                "start": 0,
                "end": len(header_text),
                "type": "email_headers",
                "preserve_boundary": True,
            })

        # Body annotation
        body_start = len("\n".join(lines[:header_end])) + 1
        annotations.append({
            "start": body_start,
            "end": len(content),
            "type": "email_body",
            "subject": headers.get("subject", ""),
            "preserve_boundary": False,
        })

        return annotations
