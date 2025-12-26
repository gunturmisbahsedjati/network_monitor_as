# Gunakan image Python ringan
FROM python:3.9-slim

# Install utilitas ping (Wajib untuk aplikasi ini)
RUN apt-get update && apt-get install -y iputils-ping && rm -rf /var/lib/apt/lists/*

# Set folder kerja
WORKDIR /app

# Copy requirements dan install dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh source code
COPY app/ .

# Expose port Flask
EXPOSE 5000

# Jalankan aplikasi
CMD ["python", "app.py"]