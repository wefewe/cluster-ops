# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend Runtime
FROM python:3.12-alpine
RUN apk add --no-cache openssh-client curl
WORKDIR /app
COPY server.py /app/server.py
COPY ops /app/ops
COPY --from=frontend-builder /app/frontend/dist /app/dist
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/api/auth-check || exit 1
CMD ["python3", "-u", "/app/server.py"]
