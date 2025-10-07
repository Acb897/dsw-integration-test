# ========== 1. Base image ==========
FROM python:3.12-slim

# ========== 2. Set working dir ==========
WORKDIR /app

# ========== 3. Copy & install dependencies ==========
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ========== 4. Copy app code ==========
COPY . .

# ========== 5. Expose FastAPI port ==========
EXPOSE 8000

# ========== 6. Run FastAPI server ==========
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
