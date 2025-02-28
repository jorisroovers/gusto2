FROM python:3.12-slim

WORKDIR /app

# Install UV
RUN pip install --no-cache-dir uv

# Copy project configuration and app code
COPY . .

# Install dependencies using UV with the --system flag
RUN uv sync

# Make sure the Python path is set correctly
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Start application using UV
CMD ["sh", "-c", "uv run uvicorn gusto2.main:app --host 0.0.0.0 --port 8000 --reload"]
