from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # Database
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # Embedding Model
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 2000
    openai_timeout: int = 60

    # 배치 설정
    clustering_n_clusters: int = 8
    clustering_top_n: int = 10
    clustering_schedule_cron: str = "0 3 * * 0"  # 매주 일요일 새벽 3시
    log_level: str = "INFO"
    log_dir: str = "logs"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """설정 인스턴스를 반환 (싱글톤)"""
    return Settings()
