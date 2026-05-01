FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
COPY migrations/ migrations/
COPY data/ data/
RUN pip install --no-cache-dir -e . && mkdir -p /app/storage
CMD ["python3", "-m", "kartuli_bot.main"]
