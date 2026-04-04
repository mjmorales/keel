FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/mjmorales/keel"
LABEL org.opencontainers.image.description="Keel — architectural contract enforcement for LLM-driven codebases"

WORKDIR /app
COPY README.md /app/README.md
COPY skill.manifest /app/skill.manifest
COPY SKILL.md /app/SKILL.md
COPY references/ /app/references/
COPY assets/ /app/assets/
COPY cli/ /app/cli/

RUN pip install --no-cache-dir ./cli

WORKDIR /project
ENTRYPOINT ["keel"]
