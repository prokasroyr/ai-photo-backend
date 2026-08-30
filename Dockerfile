FROM python:3.10-slim

# dlib ও face_recognition কম্পাইল করার জন্য প্রয়োজনীয় টুলস ইনস্টল
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    libx11-dev \
    libgtk-3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# pip আপগ্রেড ও প্যাকেজ ইনস্টল
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Uvicorn রান করা
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]