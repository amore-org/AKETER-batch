# Python 3.12 + uv 멀티스테이지 빌드
FROM python:3.12-slim AS builder

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 작업 디렉토리 설정
WORKDIR /build

# 시스템 의존성 설치 (빌드용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# pyproject.toml 복사 및 의존성 설치
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

# 최종 실행 이미지
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (런타임용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# builder 스테이지에서 설치한 Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

ENV PYTHONUNBUFFERED=1

# 애플리케이션 코드 복사
COPY ./app /app/app

# ChromaDB 데이터 디렉토리 생성
RUN mkdir -p /app/chroma_db

# 볼륨 설정 (ChromaDB 데이터 영구 저장)
VOLUME ["/app/chroma_db"]

# 포트 노출
EXPOSE 8000

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
