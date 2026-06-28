
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app


COPY requirements.txt .

# Install dependencies cleanly
RUN pip install --no-cache-dir -r requirements.txt


COPY . .

# Expose the port Railway will use dynamically
EXPOSE 8000

# Run the Uvicorn production server bound to Railway's dynamic PORT environment variable
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]