from sqlalchemy import Column, BigInteger, String, Integer, DateTime, Text
from datetime import datetime

from .base import Base


class Persona(Base):
    """페르소나 테이블"""
    __tablename__ = "persona"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    profile_text = Column(Text, nullable=True)  # LLM 생성 프로필
    member_count = Column(Integer, default=0, nullable=True)
    message_id = Column(BigInteger, unique=True, nullable=True)

    # 타임스탬프
    created_at = Column(DateTime(6), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(6), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Persona(id={self.id}, name={self.name}, member_count={self.member_count})>"
