FROM condaforge/miniforge3:latest

WORKDIR /app

# Pre-compiled dlib ও face_recognition ইনস্টল (কোনো C++ কম্পাইলেশন হবে না)
RUN conda install -y -c conda-forge dlib face_recognition python=3.10

COPY requirements.txt .

# বাকি পাইথন প্যাকেজ ইনস্টল
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]