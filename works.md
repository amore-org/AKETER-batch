# AKETER-batch 작업 내용 요약

## 작업 개요
페르소나 대표 피처와 아이템 피처를 레이블과 함께 문장으로 변환하여 ChromaDB에 벡터화하여 저장하는 인덱싱 시스템 구현

## 구현 내용

### 1. 프로젝트 구조 설정
- **requirements.txt**: 필요한 라이브러리 의존성 정의
  - chromadb: 벡터 데이터베이스
  - sentence-transformers: 임베딩 모델
  - sqlalchemy, pymysql: 데이터베이스 연결
  - pydantic, python-dotenv: 설정 관리

- **.env.example**: 환경 변수 템플릿 생성
  - 데이터베이스 연결 정보
  - ChromaDB 저장 경로
  - 임베딩 모델 설정

### 2. 데이터베이스 모델 정의 (`app/models/`)
- **persona.py**: 페르소나 대표 피처 모델
  - PersonaRepresentativeFeature 클래스
  - 연령대, 카테고리, 키워드, 민감도, 충성도, 스타일 등 ENUM 정의

- **item.py**: 아이템 피처 모델
  - ItemFeature 클래스
  - 카테고리, 가격 포지션, 프로모션 타입 등 ENUM 정의

### 3. 텍스트 빌더 유틸리티 (`app/utils/text_builder.py`)
**핵심 기능: 레이블 포함 문장 변환**

#### PersonaTextBuilder
- 페르소나 피처를 레이블과 함께 한글 문장으로 변환
- 예시: `"연령대: 30대 카테고리: 스킨케어 핵심키워드: 비타민A 가격민감도: 가성비"`
- ENUM 값을 한글로 변환하여 가독성 향상
- 성능 최적화를 위해 필드명(레이블)과 값을 함께 포함

#### ItemTextBuilder
- 아이템 피처를 레이블과 함께 한글 문장으로 변환
- 예시: `"제품명: 비타민C세럼 카테고리: 스킨케어 가격포지션: 가성비"`
- 제품명, 카테고리, 타겟 연령대, 가격 포지션, 프로모션 타입 등을 조합

**레이블 포함의 장점:**
- 임베딩 모델이 필드의 의미를 더 정확하게 이해
- 검색 시 필드별 필터링 및 가중치 적용 가능
- 벡터 공간에서 더 의미있는 클러스터링

### 4. ChromaDB 클라이언트 (`app/utils/chroma_client.py`)
- **ChromaDBClient 클래스**
  - SentenceTransformer를 사용한 임베딩 생성
  - 한국어 지원 임베딩 모델 사용 (`paraphrase-multilingual-MiniLM-L12-v2`)
  - 배치 upsert 지원
  - 유사도 검색 기능
  - 메타데이터 필터링 지원

### 5. 인덱싱 로직 (`app/indexing/`)
#### PersonaIndexer (`persona_indexer.py`)
- 페르소나 대표 피처를 ChromaDB에 인덱싱
- 배치 처리로 대량 데이터 효율적 처리
- 페르소나별 검색 및 조회 기능

#### ItemIndexer (`item_indexer.py`)
- **아이템 피처를 ChromaDB에 인덱싱** (요구사항 구현)
- item_id를 ID로 사용하여 벡터 저장
- 배치 처리 (기본 100개씩)
- 텍스트 빌더로 레이블 포함 문장 생성 → 임베딩 → ChromaDB 저장
- 카테고리 필터링을 통한 검색 최적화

**인덱싱 프로세스:**
1. DB에서 item_feature 조회
2. ItemTextBuilder로 레이블 포함 문장 변환
3. SentenceTransformer로 벡터화
4. ChromaDB에 item_id로 저장

### 6. LLM 호출 모듈 (`app/llm/`) - 신규 추가
**ChatGPT 연결을 위한 LLM 클라이언트 모듈 (나중에 붙을 기능)**

#### LLMClient (`llm/client.py`)
- **OpenAI ChatGPT API 연결 클라이언트**
  - OpenAI Python SDK를 사용한 ChatGPT API 호출
  - Tenacity를 사용한 자동 재시도 로직 (최대 3회)
  - API 오류, 연결 오류, Rate Limit 오류 처리

- **주요 메서드:**
  - `chat_completion()`: 기본 채팅 완성 API 호출
  - `generate_text()`: 단순 프롬프트로 텍스트 생성
  - `chat()`: 대화 히스토리를 포함한 대화형 채팅
  - `stream_completion()`: 스트리밍 응답 지원
  - `get_embedding()`: OpenAI 임베딩 생성

- **설정 가능한 파라미터:**
  - model: 사용할 모델 (기본값: gpt-4o-mini)
  - temperature: 응답의 창의성 조절 (0.0~2.0)
  - max_tokens: 최대 토큰 수
  - timeout: API 호출 타임아웃

#### PromptTemplate (`llm/prompts.py`)
- **프롬프트 템플릿 관리 시스템**
  - 템플릿 기반 프롬프트 생성 (Python Template 사용)
  - 시스템 메시지와 사용자 메시지 분리 관리
  - 변수 치환을 통한 동적 프롬프트 생성

- **미리 정의된 템플릿 (PromptTemplates):**
  1. `CRM_MESSAGE_GENERATION`: CRM 메시지 자동 생성
     - 페르소나와 추천 아이템 정보로 개인화 메시지 생성
  2. `PRODUCT_RECOMMENDATION_EXPLANATION`: 상품 추천 이유 설명
     - 페르소나에게 왜 이 상품을 추천하는지 설명
  3. `PERSONA_SUMMARY`: 페르소나 데이터 요약
     - 복잡한 페르소나 데이터를 자연스러운 문장으로 요약
  4. `PRODUCT_DESCRIPTION`: 제품 설명 생성
     - 제품 정보로 매력적인 마케팅 카피 작성
  5. `CUSTOMER_SERVICE`: 고객 응대
     - 고객 문의에 친절하고 전문적으로 답변

#### Examples (`llm/examples.py`)
- **LLM 클라이언트 사용 예시 코드**
  - 기본 채팅, 대화형 채팅, 템플릿 사용 등 다양한 예시
  - 페르소나 정보로 CRM 메시지 생성하는 실제 사용 시나리오
  - 스트리밍 응답, 파라미터 조정 예시

**통합 활용 시나리오:**
```python
# 페르소나 정보 조회
persona = db.query(PersonaRepresentativeFeature).first()
persona_text = PersonaTextBuilder.build(persona)

# ChromaDB에서 유사한 아이템 검색
indexer = ItemIndexer()
similar_items = indexer.search_similar_items(persona_text, n_results=3)

# LLM으로 개인화된 CRM 메시지 생성
llm_client = LLMClient()
crm_message = llm_client.generate_text(
    prompt=create_crm_message_prompt(persona_text, similar_items),
    system_message=PromptTemplates.CRM_MESSAGE_GENERATION.system_message
)
```

### 7. FastAPI 웹 서버 구조 (`app/main.py`, `app/api/`, `app/schemas/`)
**프로젝트를 FastAPI 기반 RESTful API로 전환**

#### API 스키마 (`app/schemas/`)
- **indexing.py**: 인덱싱 요청/응답 스키마
- **search.py**: 검색 요청/응답 스키마
- **llm.py**: LLM 요청/응답 스키마 (텍스트 생성, 채팅, CRM 메시지 등)

#### API 라우터 (`app/api/`)

**1. 인덱싱 API (`app/api/indexing.py`)**
- `POST /api/indexing/items`: 아이템 인덱싱
- `POST /api/indexing/personas`: 페르소나 인덱싱
- `POST /api/indexing/all`: 전체 인덱싱
- `GET /api/indexing/items/count`: 아이템 개수 조회
- `GET /api/indexing/personas/count`: 페르소나 개수 조회

**2. 검색 API (`app/api/search.py`)**
- `POST /api/search/items`: 아이템 검색 (POST)
- `GET /api/search/items/{query}`: 아이템 검색 (GET)
- `POST /api/search/personas`: 페르소나 검색 (POST)
- `GET /api/search/personas/{query}`: 페르소나 검색 (GET)

**3. LLM API (`app/api/llm.py`)**
- `POST /api/llm/generate`: 텍스트 생성
- `POST /api/llm/chat`: 대화형 채팅
- `POST /api/llm/crm-message`: CRM 메시지 생성
- `GET /api/llm/templates`: 프롬프트 템플릿 목록
- `GET /api/llm/health`: LLM 서비스 상태 확인

#### 메인 애플리케이션 (`app/main.py`)
- FastAPI 앱 인스턴스 생성 및 설정
- CORS 미들웨어 설정
- 모든 라우터 통합
- Swagger UI (`/docs`), ReDoc (`/redoc`) 자동 생성
- 헬스 체크 및 API 정보 엔드포인트

**서버 실행:**
```bash
# 개발 서버 실행
uvicorn app.main:app --reload

# 또는
python -m app.main
```

**API 문서 접근:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- API 정보: http://localhost:8000/api/info

## 기술 스택
- **웹 프레임워크**: FastAPI
- **벡터 DB**: ChromaDB (로컬 영구 저장)
- **임베딩 모델**: SentenceTransformer (다국어 지원)
- **LLM**: OpenAI ChatGPT API (gpt-5-mini)
- **ORM**: SQLAlchemy
- **DB 드라이버**: PyMySQL
- **설정 관리**: Pydantic Settings
- **재시도 로직**: Tenacity
- **ASGI 서버**: Uvicorn

## 주요 특징
1. ✅ **FastAPI 기반 RESTful API**: 자동 문서 생성, 타입 검증, 비동기 처리
2. ✅ **레이블 포함 문장 변환**: 필드명과 값을 함께 포함하여 임베딩 품질 향상
3. ✅ **한글 레이블 사용**: 가독성 및 검색 정확도 향상
4. ✅ **배치 처리**: 대량 데이터 효율적 인덱싱
5. ✅ **ENUM 한글 변환**: 사용자 친화적 텍스트 생성
6. ✅ **Upsert 지원**: 중복 없이 업데이트 가능
7. ✅ **메타데이터 저장**: 추가 정보를 통한 필터링 및 분석
8. ✅ **LLM 통합**: ChatGPT API를 통한 개인화 메시지 생성
9. ✅ **프롬프트 템플릿**: 재사용 가능한 프롬프트 템플릿 시스템
10. ✅ **자동 재시도**: API 오류 시 자동 재시도 로직
11. ✅ **Swagger UI**: 대화형 API 문서 자동 생성
12. ✅ **Docker 컨테이너화**: 멀티스테이지 빌드, 볼륨 관리, 헬스체크
13. ✅ **Docker Compose**: MySQL + FastAPI + ChromaDB 통합 실행

## 디렉토리 구조
```
AKETER-batch/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 메인 애플리케이션
│   ├── config.py               # 설정 관리 (DB, ChromaDB, OpenAI)
│   ├── database.py             # DB 연결 관리
│   ├── models/                 # SQLAlchemy 데이터 모델
│   │   ├── __init__.py
│   │   ├── persona.py          # 페르소나 모델
│   │   └── item.py             # 아이템 모델
│   ├── schemas/                # Pydantic API 스키마 (신규)
│   │   ├── __init__.py
│   │   ├── indexing.py         # 인덱싱 요청/응답 스키마
│   │   ├── search.py           # 검색 요청/응답 스키마
│   │   └── llm.py              # LLM 요청/응답 스키마
│   ├── api/                    # FastAPI 라우터 (신규)
│   │   ├── __init__.py
│   │   ├── indexing.py         # 인덱싱 API 엔드포인트
│   │   ├── search.py           # 검색 API 엔드포인트
│   │   └── llm.py              # LLM API 엔드포인트
│   ├── utils/                  # 유틸리티
│   │   ├── __init__.py
│   │   ├── text_builder.py     # 텍스트 빌더 (레이블 포함 문장 변환)
│   │   └── chroma_client.py    # ChromaDB 클라이언트
│   ├── indexing/               # 인덱싱 로직
│   │   ├── __init__.py
│   │   ├── persona_indexer.py  # 페르소나 인덱서
│   │   └── item_indexer.py     # 아이템 인덱서
│   └── llm/                    # LLM 호출 모듈
│       ├── __init__.py
│       ├── client.py           # OpenAI ChatGPT 클라이언트
│       ├── prompts.py          # 프롬프트 템플릿 관리
│       └── examples.py         # 사용 예시 코드
├── requirements.txt            # 의존성 패키지 (FastAPI, OpenAI 등)
├── .env.example                # 환경 변수 템플릿
├── Dockerfile                  # Docker 이미지 빌드 설정 (신규)
├── docker-compose.yml          # Docker Compose 설정 (신규)
├── .dockerignore               # Docker 빌드 제외 파일
├── DOCKER.md                   # Docker 실행 가이드 (신규)
├── README.md                   # 프로젝트 설명서
└── works.md                    # 작업 내용 요약 (본 파일)
```

## Docker 컨테이너화 (신규)

### Dockerfile
- **멀티스테이지 빌드**: 빌드와 런타임 단계 분리로 이미지 크기 최적화
- **Python 3.11 slim 이미지** 사용
- **ChromaDB 볼륨**: `/app/chroma_db`를 볼륨으로 마운트하여 데이터 영구 저장
- **헬스체크**: 애플리케이션 상태 자동 모니터링

### docker-compose.yml
전체 서비스 오케스트레이션:

**1. MySQL 서비스**
- MySQL 8.0 이미지
- 포트: 3306
- 데이터 볼륨: `mysql_data`
- 헬스체크 포함

**2. API 서비스 (FastAPI + ChromaDB)**
- FastAPI 애플리케이션
- 포트: 8000
- ChromaDB 데이터 볼륨: `chroma_data`
- 환경 변수로 설정 주입
- MySQL 서비스 의존성 설정

**볼륨**:
- `mysql_data`: MySQL 데이터 영구 저장
- `chroma_data`: ChromaDB 벡터 데이터 영구 저장

**네트워크**:
- `aketer-network`: 서비스 간 통신을 위한 브리지 네트워크

### Docker 실행 방법

```bash
# 1. 환경 변수 설정
cp .env.example .env
# .env 파일에서 OPENAI_API_KEY 설정

# 2. 서비스 실행
docker-compose up -d

# 3. 로그 확인
docker-compose logs -f

# 4. 서비스 접속
# - Swagger UI: http://localhost:8000/docs
# - API: http://localhost:8000
# - MySQL: localhost:3306
```

### Docker 주요 명령어

```bash
# 빌드 후 실행
docker-compose up --build -d

# 서비스 중지
docker-compose stop

# 서비스 재시작
docker-compose restart

# 컨테이너 및 볼륨 삭제 (데이터 손실 주의)
docker-compose down -v

# 로그 실시간 확인
docker-compose logs -f api

# 컨테이너 접속
docker-compose exec api bash
```

### 데이터 영구성
- **ChromaDB**: `chroma_data` 볼륨에 벡터 데이터 저장
- **MySQL**: `mysql_data` 볼륨에 관계형 데이터 저장
- 컨테이너 재시작 시에도 데이터 유지

## 다음 단계 제안
1. **API 테스트 및 검증**
   - 실제 데이터베이스 연결 및 인덱싱 테스트
   - API 엔드포인트 통합 테스트
   - Swagger UI를 통한 수동 테스트

2. **성능 최적화**
   - 임베딩 모델 성능 평가 및 최적화
   - 검색 정확도 평가
   - 벡터 인덱스 튜닝 (dimension, distance metric 등)
   - API 응답 시간 최적화

3. **통합 워크플로우 구축**
   - 페르소나 분석 → 아이템 추천 → CRM 메시지 생성 통합 엔드포인트
   - 배치 작업 스케줄러 추가 (APScheduler 등)

4. **배포 및 운영**
   - ✅ Docker 컨테이너화 완료
   - Docker Swarm 또는 Kubernetes 오케스트레이션
   - 환경별 설정 관리 (개발/스테이징/프로덕션)
   - 로깅 및 모니터링 시스템 구축 (Prometheus, Grafana)
   - API 인증/권한 관리 (JWT, OAuth 등)
   - CI/CD 파이프라인 구축 (GitHub Actions, GitLab CI)

5. **품질 개선**
   - 프롬프트 엔지니어링 및 A/B 테스트
   - LLM 응답 품질 평가 메트릭
   - 단위 테스트 및 통합 테스트 작성

6. **문서화**
   - API 사용 가이드 작성
   - 예제 코드 및 튜토리얼 추가
   - 운영 매뉴얼 작성
