FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/mjmorales/keel"
LABEL org.opencontainers.image.description="Keel — architectural contract enforcement for LLM-driven codebases"

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir .

WORKDIR /project
ENTRYPOINT ["keel"]
