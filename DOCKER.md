# Docker 실행 가이드

## 사전 요구사항

- Docker 설치 (Docker Desktop 권장)
- Docker Compose 설치 (Docker Desktop에 포함)

## 빠른 시작

### 1. 환경 변수 설정

`.env` 파일을 생성하고 OpenAI API 키를 설정합니다:

```bash
# Linux/Mac
cp .env.example .env

# Windows
copy .env.example .env
```

`.env` 파일에서 OpenAI API 키를 실제 키로 변경:
```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 2. Docker Compose로 전체 서비스 실행

```bash
# 백그라운드에서 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그만 확인
docker-compose logs -f api
```

### 3. 서비스 접속

- **API 문서 (Swagger UI)**: http://localhost:8000/docs
- **API 문서 (ReDoc)**: http://localhost:8000/redoc
- **API 정보**: http://localhost:8000/api/info
- **헬스 체크**: http://localhost:8000/health
- **MySQL**: localhost:3306 (aketer_user/aketer_password)

## Docker 명령어

### 빌드 및 실행

```bash
# 이미지 빌드 후 실행
docker-compose up --build

# 백그라운드에서 실행
docker-compose up -d

# 특정 서비스만 실행
docker-compose up -d api
docker-compose up -d mysql
```

### 서비스 관리

```bash
# 서비스 중지
docker-compose stop

# 서비스 시작
docker-compose start

# 서비스 재시작
docker-compose restart

# 서비스 중지 및 컨테이너 삭제
docker-compose down

# 볼륨까지 모두 삭제 (주의: 데이터 손실)
docker-compose down -v
```

### 로그 확인

```bash
# 전체 로그 확인
docker-compose logs

# 실시간 로그 확인
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f api
docker-compose logs -f mysql

# 최근 100줄만 확인
docker-compose logs --tail=100 api
```

### 컨테이너 접속

```bash
# API 컨테이너 접속
docker-compose exec api bash

# MySQL 컨테이너 접속
docker-compose exec mysql bash

# MySQL CLI 접속
docker-compose exec mysql mysql -u aketer_user -paketer_password aketer_db
```

## Docker만 사용 (Compose 없이)

### 이미지 빌드

```bash
docker build -t aketer-api .
```

### 컨테이너 실행

```bash
docker run -d \
  --name aketer-api \
  -p 8000:8000 \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=3306 \
  -e DB_NAME=aketer_db \
  -e DB_USER=aketer_user \
  -e DB_PASSWORD=aketer_password \
  -e OPENAI_API_KEY=sk-your-api-key-here \
  aketer-api
```

## 데이터 영구 저장

### 볼륨 관리

```bash
# 볼륨 목록 확인
docker volume ls

# ChromaDB 볼륨 확인
docker volume inspect aketer-batch_chroma_data

# MySQL 볼륨 확인
docker volume inspect aketer-batch_mysql_data
```

### 데이터 백업

```bash
# ChromaDB 데이터 백업
docker run --rm -v aketer-batch_chroma_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/chroma_backup.tar.gz -C /data .

# MySQL 데이터 백업
docker-compose exec mysql mysqldump -u aketer_user -paketer_password aketer_db > backup.sql
```

### 데이터 복원

```bash
# ChromaDB 데이터 복원
docker run --rm -v aketer-batch_chroma_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/chroma_backup.tar.gz -C /data

# MySQL 데이터 복원
docker-compose exec -T mysql mysql -u aketer_user -paketer_password aketer_db < backup.sql
```

## 트러블슈팅

### 포트 충돌

포트가 이미 사용 중인 경우 `docker-compose.yml`에서 포트를 변경:

```yaml
services:
  api:
    ports:
      - "8001:8000"  # 8000 대신 8001 사용
```

### 컨테이너 재시작

```bash
# 모든 컨테이너 재시작
docker-compose restart

# API 컨테이너만 재시작
docker-compose restart api
```

### 로그 디버깅

```bash
# 상세 로그 확인
docker-compose logs -f --tail=1000 api

# 컨테이너 상태 확인
docker-compose ps

# 컨테이너 리소스 사용량 확인
docker stats
```

### 완전 초기화

```bash
# 모든 컨테이너, 네트워크, 볼륨 삭제
docker-compose down -v

# 이미지 삭제
docker rmi aketer-batch_api

# 재빌드 및 실행
docker-compose up --build -d
```

## 프로덕션 배포

### 환경별 설정

프로덕션 환경을 위한 `docker-compose.prod.yml` 생성:

```yaml
version: '3.8'

services:
  api:
    restart: always
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    # 코드 볼륨 마운트 제거
```

실행:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 보안 고려사항

1. `.env` 파일을 git에 커밋하지 않기
2. 프로덕션에서는 강력한 데이터베이스 비밀번호 사용
3. CORS 설정을 특정 도메인으로 제한
4. API 인증/권한 추가

## 성능 최적화

### 리소스 제한

`docker-compose.yml`에 리소스 제한 추가:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### 헬스체크 튜닝

필요에 따라 헬스체크 간격 조정:

```yaml
healthcheck:
  interval: 60s
  timeout: 10s
  retries: 3
```

## 참고 자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 공식 문서](https://docs.docker.com/compose/)
- [FastAPI Docker 가이드](https://fastapi.tiangolo.com/deployment/docker/)
