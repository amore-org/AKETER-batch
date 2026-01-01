"""아이템 모델"""
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime
from datetime import datetime

from .base import Base


class Item(Base):
    """아이템 테이블"""
    __tablename__ = "item"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 아이템 정보
    item_key = Column(String(64), unique=True, nullable=True, index=True)
    name = Column(String(200), nullable=False)
    meta_path = Column(String(500), nullable=False)

    # 활성화 여부
    is_active = Column(Boolean, nullable=False, default=True)

    # 타임스탬프
    created_at = Column(DateTime(6), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(6), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name}', is_active={self.is_active})>"
