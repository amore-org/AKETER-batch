# AKETER-batch

CRM 메시지 자동 제작 AI agent Python batch

## 프로젝트 개요

페르소나 대표 피처와 아이템 피처를 벡터화하여 ChromaDB에 저장하는 인덱싱 시스템입니다.
레이블과 함께 문장으로 변환하여 임베딩 모델의 성능을 최적화했습니다.

## 주요 기능

- ✅ 페르소나 대표 피처 인덱싱 (레이블 포함)
- ✅ 아이템 피처 인덱싱 (레이블 포함)
- ✅ ChromaDB 벡터 저장
- ✅ 유사도 기반 검색
- ✅ 배치 처리 지원

## 설치 방법

### 1. 가상환경 생성 및 활성화

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 설정을 입력합니다.

```bash
cp .env.example .env
```

`.env` 파일 예시:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password

CHROMA_PERSIST_DIR=./chroma_db
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

## 사용 방법

### 아이템 인덱싱

```bash
python -m app.main index-items --batch-size 100
```

### 페르소나 인덱싱

```bash
python -m app.main index-personas --batch-size 100
```

### 전체 인덱싱

```bash
python -m app.main index-all
```

### 아이템 검색 (테스트)

```bash
python -m app.main search-items "30대 스킨케어 가성비" --n-results 10
```

## 프로젝트 구조

```
AKETER-batch/
├── app/
│   ├── __init__.py
│   ├── main.py                 # 메인 실행 파일
│   ├── config.py               # 설정 관리
│   ├── database.py             # DB 연결 관리
│   ├── models/                 # 데이터 모델
│   │   ├── __init__.py
│   │   ├── persona.py          # 페르소나 모델
│   │   └── item.py             # 아이템 모델
│   ├── utils/                  # 유틸리티
│   │   ├── __init__.py
│   │   ├── text_builder.py     # 텍스트 빌더 (레이블 포함 문장 변환)
│   │   └── chroma_client.py    # ChromaDB 클라이언트
│   └── indexing/               # 인덱싱 로직
│       ├── __init__.py
│       ├── persona_indexer.py  # 페르소나 인덱서
│       └── item_indexer.py     # 아이템 인덱서
├── requirements.txt            # 의존성 패키지
├── .env.example                # 환경 변수 템플릿
├── README.md                   # 프로젝트 설명서 (본 파일)
└── works.md                    # 작업 내용 요약
```

## 기술 스택

- **Python**: 3.8+
- **벡터 DB**: ChromaDB
- **임베딩 모델**: SentenceTransformer (다국어 지원)
- **ORM**: SQLAlchemy
- **DB**: MySQL (PyMySQL 드라이버)
- **설정 관리**: Pydantic Settings

## 레이블 포함 문장 변환

### 페르소나 예시

```
연령대: 30대 카테고리: 스킨케어 핵심키워드: 비타민A 가격민감도: 가성비
```

### 아이템 예시

```
제품명: 비타민C세럼 카테고리: 스킨케어 가격포지션: 가성비 프로모션타입: 이벤트
```

**레이블 포함의 장점:**
- 임베딩 모델이 필드의 의미를 더 정확하게 이해
- 벡터 공간에서 더 의미있는 클러스터링
- 검색 시 필드별 가중치 적용 가능

## 작업 내용

자세한 작업 내용은 [works.md](./works.md)를 참고하세요.

## 라이선스

MIT License

## 프로젝트 개요

페르소나 대표 피처와 아이템 피처를 벡터화하여 ChromaDB에 저장하는 인덱싱 시스템입니다.
레이블과 함께 문장으로 변환하여 임베딩 모델의 성능을 최적화했습니다.

## 주요 기능

- ✅ 페르소나 대표 피처 인덱싱 (레이블 포함)
- ✅ 아이템 피처 인덱싱 (레이블 포함)
- ✅ ChromaDB 벡터 저장
- ✅ 유사도 기반 검색
- ✅ 배치 처리 지원

## 설치 방법

### 1. 가상환경 생성 및 활성화

```bash
1. uv install
2. uv pip install -r requirements.txt
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 설정을 입력합니다.

```bash
cp .env.example .env
```

`.env` 파일 예시:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password

CHROMA_PERSIST_DIR=./chroma_db
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

## 사용 방법

### 아이템 인덱싱

```bash
python -m app.main index-items --batch-size 100
```

### 페르소나 인덱싱

```bash
python -m app.main index-personas --batch-size 100
```

### 전체 인덱싱

```bash
python -m app.main index-all
```

### 아이템 검색 (테스트)

```bash
python -m app.main search-items "30대 스킨케어 가성비" --n-results 10
```

## 프로젝트 구조

```
AKETER-batch/
├── app/
│   ├── __init__.py
│   ├── main.py                 # 메인 실행 파일
│   ├── config.py               # 설정 관리
│   ├── database.py             # DB 연결 관리
│   ├── models/                 # 데이터 모델
│   │   ├── __init__.py
│   │   ├── persona.py          # 페르소나 모델
│   │   └── item.py             # 아이템 모델
│   ├── utils/                  # 유틸리티
│   │   ├── __init__.py
│   │   ├── text_builder.py     # 텍스트 빌더 (레이블 포함 문장 변환)
│   │   └── chroma_client.py    # ChromaDB 클라이언트
│   └── indexing/               # 인덱싱 로직
│       ├── __init__.py
│       ├── persona_indexer.py  # 페르소나 인덱서
│       └── item_indexer.py     # 아이템 인덱서
├── requirements.txt            # 의존성 패키지
├── .env.example                # 환경 변수 템플릿
├── README.md                   # 프로젝트 설명서 (본 파일)
└── works.md                    # 작업 내용 요약
```

## 기술 스택

- **Python**: 3.8+
- **벡터 DB**: ChromaDB
- **임베딩 모델**: SentenceTransformer (다국어 지원)
- **ORM**: SQLAlchemy
- **DB**: MySQL (PyMySQL 드라이버)
- **설정 관리**: Pydantic Settings

## 레이블 포함 문장 변환

### 페르소나 예시

```
연령대: 30대 카테고리: 스킨케어 핵심키워드: 비타민A 가격민감도: 가성비
```

### 아이템 예시

```
제품명: 비타민C세럼 카테고리: 스킨케어 가격포지션: 가성비 프로모션타입: 이벤트
```

**레이블 포함의 장점:**
- 임베딩 모델이 필드의 의미를 더 정확하게 이해
- 벡터 공간에서 더 의미있는 클러스터링
- 검색 시 필드별 가중치 적용 가능

## 작업 내용

자세한 작업 내용은 [works.md](./works.md)를 참고하세요.

## 설치
1. uv install
2. uv pip install -r requirements.txt