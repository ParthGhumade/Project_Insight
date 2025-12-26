FROM python:3.11-slim

WORKDIR /app

# COPY requirements FIRST
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# COPY the rest of the code
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
