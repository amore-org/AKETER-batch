# Cloud SQL Proxy 사용법

IP 화이트리스트 없이 안전하게 Cloud SQL에 연결하는 방법

## 1. Cloud SQL Proxy 다운로드

### Windows
```powershell
# Cloud SQL Proxy 다운로드
curl -o cloud-sql-proxy.exe https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.2/cloud-sql-proxy.x64.exe
```

## 2. GCP 인증 설정

```bash
# 서비스 계정 키 파일이 있는 경우
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\service-account-key.json

# 또는 gcloud CLI로 인증
gcloud auth application-default login
```

## 3. Cloud SQL Proxy 실행

```bash
# Cloud SQL 인스턴스 연결 이름 확인 (예: project:region:instance)
# GCP Console → Cloud SQL → 인스턴스 → 개요 → "인스턴스 연결 이름" 복사

# Proxy 실행 (로컬 3306 포트로 포워딩)
cloud-sql-proxy.exe --port=3306 YOUR_INSTANCE_CONNECTION_NAME
```

## 4. .env 파일 수정

```bash
# Proxy를 통해 연결하므로 localhost 사용
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=amore
DB_USER=team_ai_app_user
DB_PASSWORD=Amore**251221
```

## 5. 배치 실행

```bash
# Cloud SQL Proxy가 실행된 상태에서
uv run test_db_connection.py
uv run run_batch.py run-clustering
```

## 장점
- IP 화이트리스트 불필요
- 자동 SSL 암호화
- IAM 인증 지원
- 안전한 연결
