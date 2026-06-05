FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV UNO_PRIVATE_STATE_PATH=/app/src/uno_api/runtime/game_state.json
ENV UNO_SHARED_DIR=/app/shared

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY shared ./shared

EXPOSE 8000

CMD ["uvicorn", "uno_api.api:app", "--host", "0.0.0.0", "--port", "8000"]

