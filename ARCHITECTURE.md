# Mnemosyne - Complete Integrations & Format Support

**Version**: 1.0
**Status**: Implementation Specification
**Last Updated**: 2025-11-14

## Overview

This document details **ALL 50+ file formats** and **15+ external integrations** that Mnemosyne will support, with specific implementation strategies, libraries, and timeline.

---

## Part 1: File Format Support (50+ Formats)

### Architecture Overview

```
File Upload → Format Detection → Parser Selection → Content Extraction →
Text/Metadata Output → Chunking → Embedding → Storage
```

**Parser Strategy Pattern**:
```python
class DocumentParser(ABC):
    @abstractmethod
    def can_parse(self, file_path: str, mime_type: str) -> bool:
        pass

    @abstractmethod
    async def parse(self, file_path: str) -> ParsedDocument:
        pass

class ParserFactory:
    @staticmethod
    def get_parser(file_path: str, mime_type: str) -> DocumentParser:
        # Return appropriate parser based on file type
```

---

### Category 1: Documents (15 formats)

| Format | Extension | Library/Service | Notes |
|--------|-----------|----------------|-------|
| **PDF** | `.pdf` | Docling (primary), PyPDF2 (fallback) | Layout preservation, tables, images |
| **Word** | `.docx` | python-docx, Docling | Styles, comments, track changes |
| **Word Legacy** | `.doc` | antiword, textract | Convert to .docx first |
| **Rich Text** | `.rtf` | striprtf, Docling | Formatting extraction |
| **EPUB** | `.epub` | ebooklib | E-books, metadata |
| **OpenDocument** | `.odt` | odfpy, Docling | LibreOffice format |
| **Pages** | `.pages` | Unzip + extract (proprietary) | macOS iWork |
| **Plain Text** | `.txt` | Native Python | Direct read |
| **Markdown** | `.md` | mistune, markdown | Preserve structure |
| **HTML** | `.html`, `.htm` | BeautifulSoup4, trafilatura | Clean extraction |
| **XML** | `.xml` | lxml, xmltodict | Structured data |
| **LaTeX** | `.tex` | pandoc | Academic papers |
| **AsciiDoc** | `.adoc` | asciidoctor | Technical docs |
| **reStructuredText** | `.rst` | docutils | Python docs |
| **Org Mode** | `.org` | orgparse | Emacs notes |

**Implementation**:

```python
# src/parsers/document_parser.py
class PDFParser(DocumentParser):
    def __init__(self):
        self.docling = DoclingService()
        self.pypdf2 = PyPDF2Service()

    def can_parse(self, file_path: str, mime_type: str) -> bool:
        return mime_type == "application/pdf" or file_path.endswith(".pdf")

    async def parse(self, file_path: str) -> ParsedDocument:
        try:
            # Try Docling first (better layout preservation)
            return await self.docling.parse(file_path)
        except Exception as e:
            # Fallback to PyPDF2
            logger.warning(f"Docling failed, using PyPDF2: {e}")
            return await self.pypdf2.parse(file_path)

class WordParser(DocumentParser):
    def can_parse(self, file_path: str, mime_type: str) -> bool:
        return mime_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ]

    async def parse(self, file_path: str) -> ParsedDocument:
        if file_path.endswith(".doc"):
            # Convert .doc to .docx using antiword or LibreOffice
            file_path = await self.convert_to_docx(file_path)

        doc = Document(file_path)
        content = "\n".join([para.text for para in doc.paragraphs])
        metadata = {
            "title": doc.core_properties.title,
            "author": doc.core_properties.author,
            "created": doc.core_properties.created,
        }
        return ParsedDocument(content=content, metadata=metadata)
```

---

### Category 2: Presentations (5 formats)

| Format | Extension | Library/Service | Notes |
|--------|-----------|----------------|-------|
| **PowerPoint** | `.pptx` | python-pptx, Docling | Slides, speaker notes |
| **PowerPoint Legacy** | `.ppt` | libreoffice-convert, textract | Convert to .pptx |
| **Keynote** | `.key` | Unzip + extract (proprietary) | macOS iWork |
| **OpenDocument Presentation** | `.odp` | odfpy, Docling | LibreOffice Impress |
| **Google Slides** | API export | Google Slides API | Export to .pptx |

**Implementation**:

```python
# src/parsers/presentation_parser.py
class PowerPointParser(DocumentParser):
    def can_parse(self, file_path: str, mime_type: str) -> bool:
        return mime_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    async def parse(self, file_path: str) -> ParsedDocument:
        prs = Presentation(file_path)
        slides_content = []

        for idx, slide in enumerate(prs.slides):
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    slide_text.append(shape.text)

                # Extract speaker notes
                if slide.has_notes_slide:
                    notes = slide.notes_slide.notes_text_frame.text
                    slide_text.append(f"[Notes: {notes}]")

            slides_content.append({
                "slide_number": idx + 1,
                "content": "\n".join(slide_text)
            })

        return ParsedDocument(
            content="\n\n".join([s["content"] for s in slides_content]),
            metadata={
                "slide_count": len(prs.slides),
                "slides": slides_content
            }
        )
```

---

### Category 3: Spreadsheets (5 formats)

| Format | Extension | Library/Service | Notes |
|--------|-----------|----------------|-------|
| **Excel** | `.xlsx` | openpyxl, pandas | Formulas, multiple sheets |
| **Excel Legacy** | `.xls` | xlrd, pandas | Convert to .xlsx |
| **CSV** | `.csv` | pandas, csv | Delimiter detection |
| **TSV** | `.tsv` | pandas | Tab-separated |
| **Numbers** | `.numbers` | Unzip + extract (proprietary) | macOS iWork |

**Implementation**:

```python
# src/parsers/spreadsheet_parser.py
class ExcelParser(DocumentParser):
    def can_parse(self, file_path: str, mime_type: str) -> bool:
        return mime_type in [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel"
        ]

    async def parse(self, file_path: str) -> ParsedDocument:
        # Read all sheets
        excel_file = pd.ExcelFile(file_path)
        sheets_content = []

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)

            # Convert to markdown table for better RAG retrieval
            markdown_table = df.to_markdown(index=False)

            sheets_content.append({
                "sheet_name": sheet_name,
                "content": markdown_table,
                "rows": len(df),
                "columns": len(df.columns)
            })

        return ParsedDocument(
            content="\n\n".join([
                f"## Sheet: {s['sheet_name']}\n{s['content']}"
                for s in sheets_content
            ]),
            metadata={
                "sheet_count": len(sheets_content),
                "sheets": sheets_content
            }
        )

class CSVParser(DocumentParser):
    def can_parse(self, file_path: str, mime_type: str) -> bool:
        return mime_type == "text/csv" or file_path.endswith(".csv")

    async def parse(self, file_path: str) -> ParsedDocument:
        # Auto-detect delimiter
        with open(file_path, 'r') as f:
            sample = f.read(4096)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter

        # Read CSV
        df = pd.read_csv(file_path, delimiter=delimiter)
        markdown_table = df.to_markdown(index=False)

        return ParsedDocument(
            content=markdown_table,
            metadata={
                "rows": len(df),
                "columns": len(df.columns),
                "delimiter": delimiter
            }
        )
```

---

### Category 4: Images with OCR (10 formats)

| Format | Extension | Library/Service | Notes |
|--------|-----------|----------------|-------|
| **JPEG** | `.jpg`, `.jpeg` | Tesseract OCR, EasyOCR | Photo compression |
| **PNG** | `.png` | Tesseract OCR, EasyOCR | Lossless |
| **GIF** | `.gif` | Tesseract OCR | Animated support |
| **BMP** | `.bmp` | Tesseract OCR | Bitmap |
| **TIFF** | `.tiff`, `.tif` | Tesseract OCR | Multi-page support |
| **WebP** | `.webp` | Tesseract OCR | Modern format |
| **SVG** | `.svg` | cairosvg + Tesseract | Vector graphics |
| **HEIC** | `.heic` | pillow-heif + Tesseract | Apple format |
| **ICO** | `.ico` | Pillow + Tesseract | Icons |
| **PSD** | `.psd` | psd-tools + Tesseract | Photoshop |

**OCR Strategy**:
1. **Tesseract OCR** (primary): Free, local, privacy-focused
2. **EasyOCR** (fallback): Better for non-English text
3. **PaddleOCR** (optional): Good for Asian languages
4. **Cloud OCR** (optional): Google Vision API, AWS Textract for better accuracy

**Implementation**:

```python
# src/parsers/image_parser.py
class ImageParser(DocumentParser):
    def __init__(self):
        self.tesseract = TesseractOCR()
        self.easyocr = EasyOCR(['en'])  # Add more languages as needed

    def can_parse(self, file_path: str, mime_type: str) -> bool:
        return mime_type.startswith("image/")

    async def parse(self, file_path: str) -> ParsedDocument:
        # Convert to PIL Image
        image = Image.open(file_path)

        # Convert HEIC to PNG if needed
        if file_path.endswith('.heic'):
            image = await self.convert_heic(file_path)

        # Perform OCR
        try:
            # Try Tesseract first
            text = pytesseract.image_to_string(image, lang='eng')

            # If Tesseract returns empty, try EasyOCR
            if not text.strip():
                result = self.easyocr.readtext(file_path)
                text = "\n".join([item[1] for item in result])

        except Exception as e:
            logger.error(f"OCR failed: {e}")
            text = ""

        # Extract EXIF metadata
        exif_data = {}
        if hasattr(image, '_getexif') and image._getexif():
            exif = {
                ExifTags.TAGS[k]: v
                for k, v in image._getexif().items()
                if k in ExifTags.TAGS
            }
            exif_data = {
                "camera": exif.get("Model"),
                "date_taken": exif.get("DateTime"),
                "gps": exif.get("GPSInfo")
            }

        return ParsedDocument(
            content=text,
            metadata={
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "mode": image.mode,
                "exif": exif_data,
                "has_text": bool(text.strip())
            }
        )
```

---

### Category 5: Audio/Video with Transcription (10 formats)

| Format | Extension | Library/Service | Notes |
|--------|-----------|----------------|-------|
| **MP3** | `.mp3` | Whisper, AssemblyAI | Audio compression |
| **WAV** | `.wav` | Whisper, AssemblyAI | Lossless audio |
| **MP4** | `.mp4` | Whisper, FFmpeg | Video + audio |
| **WebM** | `.webm` | Whisper, FFmpeg | Web video |
| **AVI** | `.avi` | Whisper, FFmpeg | Legacy video |
| **MOV** | `.mov` | Whisper, FFmpeg | QuickTime |
| **MKV** | `.mkv` | Whisper, FFmpeg | Matroska |
| **FLAC** | `.flac` | Whisper | Lossless audio |
| **OGG** | `.ogg` | Whisper | Open format |
| **M4A** | `.m4a` | Whisper | Apple audio |

**Transcription Strategy**:
1. **Whisper** (primary): OpenAI's local model (whisper-large-v3)
2. **AssemblyAI** (cloud option): Better accuracy, speaker diarization
3. **Deepgram** (cloud option): Real-time transcription
4. **FFmpeg**: Extract audio from video files

**Implementation**:

```python
# src/parsers/media_parser.py
import whisper
import ffmpeg

class AudioVideoParser(DocumentParser):
    def __init__(self):
        self.whisper_model = whisper.load_model("base")  # or "large-v3" for better accuracy
        self.assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")

    def can_parse(self, file_path: str, mime_type: str) -> bool:
        return mime_type.startswith("audio/") or mime_type.startswith("video/")

    async def parse(self, file_path: str) -> ParsedDocument:
        # Extract audio from video if needed
        audio_path = file_path
        if mime_type.startswith("video/"):
            audio_path = await self.extract_audio(file_path)

        # Transcribe using Whisper
        try:
            result = self.whisper_model.transcribe(
                audio_path,
                language="en",  # Auto-detect or specify
                task="transcribe",
                verbose=False
            )

            transcript = result["text"]
            segments = result["segments"]

            # Format with timestamps
            timestamped_transcript = []
            for segment in segments:
                start = self.format_timestamp(segment["start"])
                end = self.format_timestamp(segment["end"])
                text = segment["text"]
                timestamped_transcript.append(f"[{start} -> {end}] {text}")

        except Exception as e:
            logger.error(f"Whisper failed, trying AssemblyAI: {e}")
            transcript, segments = await self.transcribe_assemblyai(audio_path)

        # Extract metadata
        probe = ffmpeg.probe(file_path)
        duration = float(probe['format']['duration'])

        return ParsedDocument(
            content=transcript,
            metadata={
                "duration_seconds": duration,
                "transcript_segments": len(segments),
                "language": result.get("language", "unknown"),
                "timestamped_transcript": timestamped_transcript
            }
        )

    async def extract_audio(self, video_path: str) -> str:
        """Extract audio from video using FFmpeg"""
        audio_path = video_path.rsplit('.', 1)[0] + '_audio.wav'

        (
            ffmpeg
            .input(video_path)
            .output(audio_path, acodec='pcm_s16le', ac=1, ar='16k')
            .overwrite_output()
            .run(quiet=True)
        )

        return audio_path

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """Convert seconds to HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
```

---

### Category 6: Email (3 formats)

| Format | Extension | Library/Service | Notes |
|--------|-----------|----------------|-------|
| **EML** | `.eml` | email, mailparser | Standard format |
| **MSG** | `.msg` | msg-extractor | Outlook format |
| **MBOX** | `.mbox` | mailbox | Unix mailbox |

**Implementation**:

```python
# src/parsers/email_parser.py
import email
from msg_extractor import Message

class EmailParser(DocumentParser):
    def can_parse(self, file_path: str, mime_type: str) -> bool:
        return file_path.endswith(('.eml', '.msg', '.mbox'))

    async def parse(self, file_path: str) -> ParsedDocument:
        if file_path.endswith('.msg'):
            return await self.parse_msg(file_path)
        elif file_path.endswith('.eml'):
            return await self.parse_eml(file_path)
        else:
            return await self.parse_mbox(file_path)

    async def parse_eml(self, file_path: str) -> ParsedDocument:
        with open(file_path, 'r') as f:
            msg = email.message_from_file(f)

        # Extract headers
        subject = msg.get('Subject', '')
        from_addr = msg.get('From', '')
        to_addr = msg.get('To', '')
        date = msg.get('Date', '')

        # Extract body
        body = ""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()

                if content_type == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                elif part.get_filename():
                    attachments.append({
                        "filename": part.get_filename(),
                        "content_type": content_type
                    })
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

        content = f"""
Subject: {subject}
From: {from_addr}
To: {to_addr}
Date: {date}

{body}
"""

        return ParsedDocument(
            content=content.strip(),
            metadata={
                "subject": subject,
                "from": from_addr,
                "to": to_addr,
                "date": date,
                "attachments": attachments
            }
        )

    async def parse_msg(self, file_path: str) -> ParsedDocument:
        msg = Message(file_path)

        content = f"""
Subject: {msg.subject}
From: {msg.sender}
To: {msg.to}
Date: {msg.date}

{msg.body}
"""

        return ParsedDocument(
            content=content.strip(),
            metadata={
                "subject": msg.subject,
                "from": msg.sender,
                "to": msg.to,
                "date": str(msg.date),
                "attachments": [a.longFilename for a in msg.attachments]
            }
        )
```

---

### Category 7: Code & Technical (10 formats)

| Format | Extension | Library/Service | Notes |
|--------|-----------|----------------|-------|
| **Python** | `.py` | Native | Preserve structure |
| **JavaScript** | `.js`, `.jsx` | Native | Comments, JSDoc |
| **TypeScript** | `.ts`, `.tsx` | Native | Type annotations |
| **Java** | `.java` | Native | JavaDoc |
| **C/C++** | `.c`, `.cpp`, `.h` | Native | Doxygen |
| **Go** | `.go` | Native | GoDoc |
| **Rust** | `.rs` | Native | Rustdoc |
| **Ruby** | `.rb` | Native | RDoc |
| **PHP** | `.php` | Native | PHPDoc |
| **Jupyter Notebook** | `.ipynb` | nbconvert | Cells, outputs |

**Implementation**: Direct text extraction with syntax highlighting preservation for better RAG retrieval.

---

## Part 2: External Integrations (15+ Connectors)

### Architecture Overview

```
Connector Registration → OAuth Flow → Periodic Sync →
Content Extraction → Normalization → Storage
```

**Connector Pattern**:
```python
class ExternalConnector(ABC):
    @abstractmethod
    async def authenticate(self, credentials: dict) -> bool:
        pass

    @abstractmethod
    async def list_content(self, since: datetime = None) -> List[ContentItem]:
        pass

    @abstractmethod
    async def fetch_content(self, item_id: str) -> ParsedDocument:
        pass

    @abstractmethod
    async def sync(self) -> SyncResult:
        pass
```

---

### Integration 1: Slack

**API**: Slack Web API
**OAuth Scopes**: `channels:history`, `channels:read`, `files:read`, `users:read`
**Sync Strategy**: Incremental (track last sync timestamp)

**Implementation**:
```python
# src/connectors/slack_connector.py
from slack_sdk import WebClient
from slack_sdk.oauth import AuthorizeUrlGenerator

class SlackConnector(ExternalConnector):
    def __init__(self, config: Config):
        self.client_id = config.SLACK_CLIENT_ID
        self.client_secret = config.SLACK_CLIENT_SECRET
        self.client = None

    async def authenticate(self, credentials: dict) -> bool:
        """OAuth flow or direct token"""
        access_token = credentials.get("access_token")
        self.client = WebClient(token=access_token)

        # Verify token
        response = self.client.auth_test()
        return response["ok"]

    async def list_content(self, since: datetime = None) -> List[ContentItem]:
        """List all channels and messages"""
        channels = self.client.conversations_list()["channels"]

        content_items = []
        for channel in channels:
            channel_id = channel["id"]
            channel_name = channel["name"]

            # Get messages since last sync
            oldest = since.timestamp() if since else 0
            messages = self.client.conversations_history(
                channel=channel_id,
                oldest=oldest
            )

            for message in messages["messages"]:
                content_items.append(ContentItem(
                    id=message["ts"],
                    type="slack_message",
                    channel=channel_name,
                    metadata={
                        "channel_id": channel_id,
                        "user": message.get("user"),
                        "timestamp": message["ts"]
                    }
                ))

        return content_items

    async def fetch_content(self, item_id: str) -> ParsedDocument:
        """Fetch single message with thread"""
        channel_id, ts = item_id.split(":")

        # Get message
        result = self.client.conversations_history(
            channel=channel_id,
            latest=ts,
            limit=1,
            inclusive=True
        )
        message = result["messages"][0]

        # Get thread replies if exists
        thread = []
        if message.get("thread_ts"):
            replies = self.client.conversations_replies(
                channel=channel_id,
                ts=message["thread_ts"]
            )
            thread = replies["messages"][1:]  # Skip parent

        # Format content
        content = f"Message: {message['text']}\n"

        if thread:
            content += "\nThread:\n"
            for reply in thread:
                content += f"- {reply['text']}\n"

        return ParsedDocument(
            content=content,
            metadata={
                "channel_id": channel_id,
                "user": message.get("user"),
                "timestamp": message["ts"],
                "has_thread": bool(thread),
                "reply_count": len(thread)
            }
        )

    async def sync(self) -> SyncResult:
        """Full sync workflow"""
        # Implement incremental sync with cursor pagination
        pass
```

---

### Integration 2: Notion

**API**: Notion API v1
**OAuth Scopes**: `read`
**Sync Strategy**: Incremental (last_edited_time)

**Implementation**:
```python
# src/connectors/notion_connector.py
from notion_client import AsyncClient

class NotionConnector(ExternalConnector):
    def __init__(self, config: Config):
        self.client = None

    async def authenticate(self, credentials: dict) -> bool:
        token = credentials.get("access_token")
        self.client = AsyncClient(auth=token)

        # Verify by listing users
        await self.client.users.list()
        return True

    async def list_content(self, since: datetime = None) -> List[ContentItem]:
        """List all pages and databases"""
        results = await self.client.search()

        content_items = []
        for item in results["results"]:
            if item["object"] == "page":
                last_edited = datetime.fromisoformat(
                    item["last_edited_time"].rstrip("Z")
                )

                if since is None or last_edited > since:
                    content_items.append(ContentItem(
                        id=item["id"],
                        type="notion_page",
                        title=self.extract_title(item),
                        metadata={
                            "last_edited": item["last_edited_time"],
                            "created": item["created_time"]
                        }
                    ))

        return content_items

    async def fetch_content(self, item_id: str) -> ParsedDocument:
        """Fetch Notion page content"""
        # Get page
        page = await self.client.pages.retrieve(item_id)

        # Get blocks (content)
        blocks = await self.client.blocks.children.list(item_id)

        # Convert blocks to markdown
        content = self.blocks_to_markdown(blocks["results"])

        return ParsedDocument(
            content=content,
            metadata={
                "title": self.extract_title(page),
                "created": page["created_time"],
                "last_edited": page["last_edited_time"],
                "url": page["url"]
            }
        )

    def blocks_to_markdown(self, blocks: List[dict]) -> str:
        """Convert Notion blocks to markdown"""
        markdown = []

        for block in blocks:
            block_type = block["type"]

            if block_type == "paragraph":
                text = self.extract_rich_text(block["paragraph"]["rich_text"])
                markdown.append(text)

            elif block_type == "heading_1":
                text = self.extract_rich_text(block["heading_1"]["rich_text"])
                markdown.append(f"# {text}")

            elif block_type == "heading_2":
                text = self.extract_rich_text(block["heading_2"]["rich_text"])
                markdown.append(f"## {text}")

            elif block_type == "bulleted_list_item":
                text = self.extract_rich_text(block["bulleted_list_item"]["rich_text"])
                markdown.append(f"- {text}")

            # Add more block types...

        return "\n\n".join(markdown)
```

---

### Integration 3: Confluence

**API**: Confluence REST API
**Auth**: API Token or OAuth
**Sync Strategy**: Incremental (version history)

---

### Integration 4: Gmail

**API**: Gmail API
**OAuth Scopes**: `gmail.readonly`
**Sync Strategy**: Incremental (history ID)

**Implementation**:
```python
# src/connectors/gmail_connector.py
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

class GmailConnector(ExternalConnector):
    async def authenticate(self, credentials: dict) -> bool:
        creds = Credentials(
            token=credentials["access_token"],
            refresh_token=credentials.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret
        )

        self.service = build('gmail', 'v1', credentials=creds)
        return True

    async def list_content(self, since: datetime = None) -> List[ContentItem]:
        """List emails"""
        query = ""
        if since:
            query = f"after:{since.strftime('%Y/%m/%d')}"

        results = self.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=500
        ).execute()

        messages = results.get('messages', [])

        return [
            ContentItem(id=msg['id'], type="email")
            for msg in messages
        ]

    async def fetch_content(self, item_id: str) -> ParsedDocument:
        """Fetch email content"""
        message = self.service.users().messages().get(
            userId='me',
            id=item_id,
            format='full'
        ).execute()

        headers = {h['name']: h['value'] for h in message['payload']['headers']}

        # Extract body
        body = self.extract_email_body(message['payload'])

        content = f"""
From: {headers.get('From')}
To: {headers.get('To')}
Subject: {headers.get('Subject')}
Date: {headers.get('Date')}

{body}
"""

        return ParsedDocument(
            content=content,
            metadata={
                "subject": headers.get('Subject'),
                "from": headers.get('From'),
                "to": headers.get('To'),
                "date": headers.get('Date'),
                "labels": message.get('labelIds', [])
            }
        )
```

---

### Integration 5: Google Calendar

**API**: Google Calendar API
**OAuth Scopes**: `calendar.readonly`
**Content**: Event titles, descriptions, attendees

---

### Integration 6: Jira

**API**: Jira REST API
**Auth**: API Token or OAuth
**Content**: Issues, comments, attachments

**Implementation**:
```python
# src/connectors/jira_connector.py
from jira import JIRA

class JiraConnector(ExternalConnector):
    async def authenticate(self, credentials: dict) -> bool:
        self.jira = JIRA(
            server=credentials["server"],
            basic_auth=(credentials["email"], credentials["api_token"])
        )
        return True

    async def fetch_content(self, item_id: str) -> ParsedDocument:
        """Fetch Jira issue"""
        issue = self.jira.issue(item_id)

        content = f"""
Issue: {issue.key}
Summary: {issue.fields.summary}
Description: {issue.fields.description or "No description"}
Status: {issue.fields.status.name}
Priority: {issue.fields.priority.name}

Comments:
"""

        for comment in issue.fields.comment.comments:
            content += f"\n[{comment.author.displayName}]: {comment.body}\n"

        return ParsedDocument(
            content=content,
            metadata={
                "key": issue.key,
                "type": issue.fields.issuetype.name,
                "status": issue.fields.status.name,
                "priority": issue.fields.priority.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None
            }
        )
```

---

### Integration 7: Linear

**API**: Linear GraphQL API
**Auth**: API Key or OAuth
**Content**: Issues, projects, comments

---

### Integration 8: ClickUp

**API**: ClickUp API v2
**Auth**: API Token or OAuth
**Content**: Tasks, docs, comments

---

### Integration 9: Airtable

**API**: Airtable API
**Auth**: API Key or OAuth
**Content**: Records from bases

---

### Integration 10: GitHub

**API**: GitHub REST API + GraphQL
**OAuth Scopes**: `repo`, `read:org`
**Content**: Repositories, issues, PRs, discussions

**Implementation**:
```python
# src/connectors/github_connector.py
from github import Github

class GitHubConnector(ExternalConnector):
    async def authenticate(self, credentials: dict) -> bool:
        self.github = Github(credentials["access_token"])
        self.github.get_user().login  # Verify token
        return True

    async def fetch_content(self, item_id: str) -> ParsedDocument:
        """Fetch GitHub issue/PR"""
        repo_name, issue_number = item_id.split(":")

        repo = self.github.get_repo(repo_name)
        issue = repo.get_issue(int(issue_number))

        content = f"""
Title: {issue.title}
State: {issue.state}
Author: {issue.user.login}
Created: {issue.created_at}

{issue.body}

Comments:
"""

        for comment in issue.get_comments():
            content += f"\n[{comment.user.login}]: {comment.body}\n"

        return ParsedDocument(
            content=content,
            metadata={
                "repo": repo_name,
                "number": issue.number,
                "state": issue.state,
                "labels": [label.name for label in issue.labels]
            }
        )
```

---

### Integration 11: Discord

**API**: Discord API
**Auth**: Bot Token or OAuth
**Content**: Messages, threads, channels

---

### Integration 12: YouTube

**API**: YouTube Data API v3
**OAuth Scopes**: `youtube.readonly`
**Content**: Video transcripts (via yt-dlp + Whisper)

**Implementation**:
```python
# src/connectors/youtube_connector.py
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

class YouTubeConnector(ExternalConnector):
    async def fetch_content(self, item_id: str) -> ParsedDocument:
        """Fetch YouTube video transcript"""
        video_id = item_id

        # Try official transcript first
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript = "\n".join([item['text'] for item in transcript_list])
        except:
            # Fallback to Whisper transcription
            audio_path = await self.download_audio(video_id)
            transcript = await self.transcribe_whisper(audio_path)

        # Get video metadata
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(f"https://youtube.com/watch?v={video_id}", download=False)

        return ParsedDocument(
            content=transcript,
            metadata={
                "title": info['title'],
                "channel": info['uploader'],
                "duration": info['duration'],
                "views": info['view_count'],
                "upload_date": info['upload_date']
            }
        )
```

---

### Integration 13-15: Search Engines

**Tavily API**: AI search engine
**LinkUp API**: Real-time web search
**SearxNG**: Self-hosted metasearch

---

## Implementation Timeline

### Phase 1: Core Formats (Week 2-3)
- ✅ Documents (PDF, DOCX, TXT, MD, HTML)
- ✅ Presentations (PPTX)
- ✅ Spreadsheets (XLSX, CSV)
- ✅ Images with OCR (JPG, PNG)
- ✅ Audio/Video with Whisper (MP3, MP4)

### Phase 2: Extended Formats (Week 4)
- ✅ All document formats (RTF, EPUB, ODT, Pages, etc.)
- ✅ All presentation formats (Keynote, ODP)
- ✅ All spreadsheet formats (Numbers, TSV)
- ✅ All image formats (GIF, BMP, TIFF, WebP, HEIC)
- ✅ All media formats (WAV, WebM, AVI, MOV, etc.)
- ✅ Email (EML, MSG)

### Phase 3: Priority Integrations (Week 5-6)
- ✅ Slack
- ✅ Notion
- ✅ Gmail
- ✅ GitHub
- ✅ YouTube

### Phase 4: Additional Integrations (Week 7-8)
- ✅ Confluence
- ✅ Jira
- ✅ Linear
- ✅ Discord
- ✅ Google Calendar

### Phase 5: Enterprise Integrations (Post-MVP)
- ClickUp
- Airtable
- Tavily
- LinkUp
- SearxNG
- Elasticsearch
- NotebookLM-style podcast generation

---

## API Endpoints for Integrations

### Connect Integration

**Endpoint**: `POST /integrations/{integration_name}/connect`

**Request**:
```json
{
  "credentials": {
    "access_token": "...",
    "refresh_token": "..."
  },
  "sync_config": {
    "auto_sync": true,
    "sync_frequency": "hourly",
    "filters": {
      "channels": ["general", "engineering"],
      "since": "2025-01-01T00:00:00Z"
    }
  }
}
```

**Response**:
```json
{
  "id": "int_abc123",
  "integration": "slack",
  "status": "connected",
  "last_sync": null,
  "next_sync": "2025-11-14T11:00:00Z"
}
```

### Trigger Sync

**Endpoint**: `POST /integrations/{integration_id}/sync`

**Response**:
```json
{
  "sync_id": "sync_xyz789",
  "status": "in_progress",
  "started_at": "2025-11-14T10:45:00Z",
  "items_queued": 150
}
```

### List Integrations

**Endpoint**: `GET /integrations`

**Response**:
```json
{
  "data": [
    {
      "id": "int_abc123",
      "integration": "slack",
      "status": "connected",
      "last_sync": "2025-11-14T09:00:00Z",
      "documents_synced": 450,
      "next_sync": "2025-11-14T11:00:00Z"
    }
  ]
}
```

---

## Dependencies Summary

### Document Parsing
```bash
# Core
pip install docling pypdf2 python-docx python-pptx openpyxl pandas

# Extended formats
pip install ebooklib odfpy striprtf antiword textract

# Markdown/HTML
pip install mistune markdown beautifulsoup4 trafilatura lxml

# Email
pip install msg-extractor mailparser
```

### OCR
```bash
# Tesseract
apt-get install tesseract-ocr tesseract-ocr-eng
pip install pytesseract

# EasyOCR
pip install easyocr

# Image processing
pip install Pillow pillow-heif psd-tools cairosvg
```

### Transcription
```bash
# Whisper
pip install openai-whisper

# FFmpeg
apt-get install ffmpeg
pip install ffmpeg-python

# Cloud services
pip install assemblyai deepgram-sdk
```

### Integrations
```bash
# Collaboration
pip install slack-sdk notion-client atlassian-python-api

# Google
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Development
pip install PyGithub discord.py

# Media
pip install yt-dlp youtube-transcript-api

# Search
pip install tavily linkup-sdk
```

---

## Configuration

```python
# src/config.py
class Config:
    # OCR
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    EASYOCR_LANGUAGES: List[str] = ["en"]

    # Transcription
    WHISPER_MODEL: str = "base"  # or "large-v3" for production
    ASSEMBLYAI_API_KEY: str = os.getenv("ASSEMBLYAI_API_KEY")

    # Slack
    SLACK_CLIENT_ID: str = os.getenv("SLACK_CLIENT_ID")
    SLACK_CLIENT_SECRET: str = os.getenv("SLACK_CLIENT_SECRET")

    # Notion
    NOTION_CLIENT_ID: str = os.getenv("NOTION_CLIENT_ID")
    NOTION_CLIENT_SECRET: str = os.getenv("NOTION_CLIENT_SECRET")

    # Gmail
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")

    # GitHub
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET")

    # ... more integrations
```

---

## Summary

**50+ File Formats**: ✅ ALL covered with specific libraries and implementation strategies
**15+ Integrations**: ✅ ALL planned with OAuth flows and sync strategies
**OCR**: ✅ Tesseract + EasyOCR for all image formats
**Transcription**: ✅ Whisper + AssemblyAI for all audio/video formats
**Timeline**: 8 weeks for complete implementation

This makes Mnemosyne a **comprehensive RAG-as-a-Service platform** with feature parity to Ragie.ai and beyond.
