FROM python:3.10-slim AS builder

WORKDIR /app


COPY requirements-unified.txt .
COPY requirements-optional.txt .
COPY requirements-fyers.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements-unified.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements-optional.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements-fyers.txt

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY . .


EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]