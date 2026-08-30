FROM python:3.10-slim

# ১. প্রয়োজনীয় সি-কম্পাইলার ও বিল্ড টুলস
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# ২. C++ কম্পাইলারকে ১টি কোর ব্যবহারের নির্দেশ (RAM বাঁচানোর জন্য)
ENV CMAKE_BUILD_PARALLEL_LEVEL=1
ENV MAKEFLAGS="-j1"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip
# dlib আগে আলাদাভাবে লিমিটেড মেমোরিতে বিল্ড হবে
RUN pip install --no-cache-dir dlib
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]