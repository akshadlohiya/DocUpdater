FROM python:3.11-slim

# Install system deps for Playwright and OpenCV
RUN apt-get update && apt-get install -y curl gnupg libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libgtk-3-0 ca-certificates build-essential git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install --with-deps

COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "process_run.py"]
