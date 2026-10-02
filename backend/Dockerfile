# Enterprise Knowledge Assistant - FastAPI backend
# Build context is the PROJECT ROOT (not backend/), because the code imports
# `backend.xxx` and needs the backend/ folder inside /app:
#   docker build -f backend/Dockerfile -t eka-backend .

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so this layer is cached when only code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the backend package (documents + FAISS index live in backend/data)
COPY backend/ ./backend/

EXPOSE 8000

# Run from /app so the relative paths (backend/data/...) resolve correctly.
# OPENAI_API_KEY is passed at runtime, never baked into the image.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
