# Enterprise Knowledge Assistant - Streamlit frontend
# Build context is the frontend/ folder:
#   docker build -t eka-frontend frontend

FROM python:3.11-slim

WORKDIR /app

# The UI only needs Streamlit and requests, so it has its own small requirements file
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8501

# BACKEND_URL tells the UI where the API is (set in docker-compose.yml)
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
