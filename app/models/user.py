from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, ForeignKey
from datetime import datetime

from .base import Base


class User(Base):
    """유저 테이블"""
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_key = Column(String(64), unique=True, nullable=True)
    name = Column(String(50), nullable=True)
    kakao_email = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    persona_id = Column(BigInteger, ForeignKey("persona.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(6), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(6), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, user_key={self.user_key}, is_active={self.is_active})>"
