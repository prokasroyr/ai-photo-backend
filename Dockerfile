FROM python:3.10-slim

# প্রয়োজনীয় সিস্টেম লাইব্রেরি
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    libx11-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip
# dlib-bin ব্যবহার করায় সরাসরি রেডিমেড বাইনারি ডাউনলোড হবে (কম্পাইল হবে না)
RUN pip install --no-cache-dir dlib-bin
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]