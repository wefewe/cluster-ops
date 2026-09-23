FROM python:3.12-alpine
RUN apk add --no-cache openssh-client
WORKDIR /app
COPY server.py /app/server.py
EXPOSE 8080
CMD ["python3", "-u", "/app/server.py"]
