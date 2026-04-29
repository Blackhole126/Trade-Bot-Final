# FROM python:3.10-slim

# WORKDIR /app

# COPY requirements-minimal.txt .

# RUN pip install -r --no-cache-dir requirements-minimal.txt

# COPY . .

# EXPOSE 5000

# CMD ["uvicorn", "run_hft2:app", "--reload", "--host", "0.0.0.0", "--port", "5000"]

# -------- Stage 1: Builder --------
FROM python:3.10-slim AS builder

WORKDIR /app

COPY requirements-minimal.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements-minimal.txt


# -------- Stage 2: Final Runtime --------
FROM python:3.10-slim

WORKDIR /app

# Copy only installed dependencies
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

EXPOSE 5000

CMD ["python","run_hft2.py"]