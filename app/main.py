"""
AKETER Batch - FastAPI Application
아이템 및 페르소나 인덱싱, 검색, LLM 기반 CRM 메시지 생성 API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# API 라우터 임포트 (향후 구현)
# from app.api import indexing, search, llm

# 배치 스케줄러 임포트
from app.utils.logging_config import setup_logging
from app.config import get_settings
from app.batch.scheduler import setup_scheduler, start_scheduler, shutdown_scheduler, get_scheduler_status
from app.utils.chroma_client import ChromaClient

# 설정 및 로깅 초기화
settings = get_settings()
setup_logging(log_dir=settings.log_dir, log_level=settings.log_level)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="AKETER Python Batch API",
    description="""
    AKETER 파이썬 배치 API

    ## 주요 기능
    - **페르소나 클러스터링**: KMeans 기반 유저 페르소나 자동 생성 및 대표자 선정
    - **인덱싱**: 페르소나 및 아이템 피처를 ChromaDB에 벡터화하여 저장 (예정)
    - **검색**: 유사도 기반 페르소나 및 아이템 검색 (예정)
    - **LLM**: ChatGPT를 활용한 개인화 CRM 메시지 생성 (예정)

    ## 기술 스택
    - FastAPI
    - scikit-learn (클러스터링)
    - ChromaDB (벡터 데이터베이스)
    - SentenceTransformer (임베딩)
    - OpenAI ChatGPT API
    - SQLAlchemy + PyMySQL
    - APScheduler (배치 스케줄러)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록 (향후 구현)
# app.include_router(indexing.router, prefix="/api")
# app.include_router(search.router, prefix="/api")
# app.include_router(llm.router, prefix="/api")


@app.get("/")
def read_root():
    """루트 엔드포인트"""
    return {
        "message": "AKETER Python Batch API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/scheduler/status")
def scheduler_status():
    """스케줄러 상태 조회"""
    return get_scheduler_status()

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행되는 이벤트"""
    logger.info("=" * 60)
    logger.info("AKETER Python Batch API 시작")
    logger.info("=" * 60)
    logger.info(f"API 문서: http://localhost:8000/docs")
    logger.info("=" * 60)

    # ChromaDB 컬렉션 초기화
    try:
        chroma_client = ChromaClient(host=settings.chroma_host, port=settings.chroma_port)
        chroma_client.get_or_create_collection(
            name="aketer_ethics_policy",
            metadata={"description": "AKETER 윤리 정책 컬렉션"}
        )
        logger.info("ChromaDB 'aketer_ethics_policy' 컬렉션 초기화 완료")
    except Exception as e:
        logger.error(f"ChromaDB 초기화 실패: {e}")

    # 배치 스케줄러 설정 및 시작
    setup_scheduler()
    start_scheduler()
    logger.info("배치 스케줄러 활성화 완료")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행되는 이벤트"""
    logger.info("AKETER Python Batch API 종료")

    # 배치 스케줄러 종료
    shutdown_scheduler()
    logger.info("배치 스케줄러 종료 완료")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
