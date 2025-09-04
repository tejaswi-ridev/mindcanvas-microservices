FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Generate gRPC files
COPY protos/ protos/
RUN python -m grpc_tools.protoc -I protos --python_out=app --grpc_python_out=app protos/auth.proto

COPY app/ app/

EXPOSE 8001 50051

CMD ["python", "app/main.py"]
