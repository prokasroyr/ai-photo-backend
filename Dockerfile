FROM python:3.10-slim

# OpenCV ও ছবির জন্য প্রয়োজনীয় সিস্টেমে লাইব্রেরি
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip

# ১. dlib-bin ও অন্যান্য সাপোর্ট প্যাকেজ ইনস্টল (কম্পাইল হবে না)
RUN pip install --no-cache-dir dlib-bin face-recognition-models Click Pillow

# ২. --no-deps দিয়ে face-recognition ইনস্টল (dlib কম্পাইল হওয়া আটকে দেওয়া হলো)
RUN pip install --no-cache-dir face-recognition --no-deps

# ৩. বাকি প্রজেক্ট প্যাকেজ ইনস্টল
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]