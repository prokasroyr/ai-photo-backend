FROM debian:bookworm-slim

# C++ কম্পাইল না করে সরাসরি প্রি-বিল্ড করা dlib ও face-recognition ইনস্টল
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dlib \
    python3-face-recognition \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# পাইথন প্যাকেজ ইনস্টল
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]