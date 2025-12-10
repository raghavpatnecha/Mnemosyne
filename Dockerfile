FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# libgl1, libglib2.0-0: Required by OpenCV/rapidocr (Docling 2.x OCR)
# ffmpeg: Required for video/audio processing (extract audio for Whisper transcription)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry with retry logic
RUN pip install --no-cache-dir poetry || pip install --no-cache-dir poetry

# Copy dependency files
COPY pyproject.toml poetry.lock* README.md ./

# Configure Poetry and install dependencies
# Use --no-root to skip installing the project itself during dependency installation
RUN poetry config virtualenvs.create false \
    && poetry config installer.max-workers 10 \
    && poetry install --no-root --no-interaction --no-ansi --only main

# Copy application code
COPY backend ./backend

# Create uploads directory
RUN mkdir -p /app/uploads

# Pre-download FlashRank reranker model (avoids download at runtime)
RUN python -c "from flashrank import Ranker; Ranker(model_name='ms-marco-MultiBERT-L-12')"

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
