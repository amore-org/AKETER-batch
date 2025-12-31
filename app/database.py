from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
import urllib.parse

from .config import get_settings

settings = get_settings()


def get_database_url() -> str:
    """데이터베이스 URL 생성"""
    # 비밀번호 URL 인코딩 (특수문자 처리)
    encoded_password = urllib.parse.quote_plus(settings.db_password)
    # 디버그용 출력 (필요시 주석 해제)
    # print(f"DB Host: {settings.db_host}")
    # print(f"DB User: {settings.db_user}")
    # print(f"Original Password: {settings.db_password}")
    # print(f"Encoded Password: {encoded_password}")
    return f"mysql+pymysql://{settings.db_user}:{encoded_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"


# Cloud SQL 연결 옵션
connect_args = {
    "charset": "utf8mb4",
    "connect_timeout": 30,
    "ssl": {"ssl": True},  # SSL 연결 활성화
}

# SSL 인증서 파일이 있는 경우 추가
if hasattr(settings, 'db_ssl_ca') and settings.db_ssl_ca:
    connect_args["ssl"]["ca"] = settings.db_ssl_ca
if hasattr(settings, 'db_ssl_cert') and settings.db_ssl_cert:
    connect_args["ssl"]["cert"] = settings.db_ssl_cert
if hasattr(settings, 'db_ssl_key') and settings.db_ssl_key:
    connect_args["ssl"]["key"] = settings.db_ssl_key

# SQLAlchemy 엔진 생성
engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    connect_args=connect_args,
    echo=False,  # SQL 로그 출력 (디버깅 시 True)
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션을 제공하는 컨텍스트 매니저"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
