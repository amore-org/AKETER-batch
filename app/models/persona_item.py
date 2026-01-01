"""페르소나-아이템 매칭 결과 모델"""
from sqlalchemy import Column, BigInteger, Integer, Float, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime

from .base import Base


class PersonaItem(Base):
    """페르소나-아이템 매칭 결과 테이블"""
    __tablename__ = "persona_item"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Keys
    persona_id = Column(BigInteger, ForeignKey("persona.id"), nullable=False, index=True)
    item_id = Column(BigInteger, ForeignKey("item.id"), nullable=False, index=True)

    # 매칭 결과
    item_rank = Column(Integer, nullable=True)  # 1-5 순위
    similarity_score = Column(Float, nullable=False)  # 벡터 유사도 점수
    score = Column(Float, nullable=True)  # 협업 필터링 점수 (cf_score)
    final_score = Column(Float, nullable=False)  # 최종 점수 (similarity + cf 결합)

    # 타임스탬프
    created_at = Column(DateTime(6), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(6), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Unique Constraint
    __table_args__ = (
        UniqueConstraint('persona_id', 'item_id', name='uk_persona_item'),
    )

    def __repr__(self):
        return (f"<PersonaItem(persona_id={self.persona_id}, item_id={self.item_id}, "
                f"rank={self.item_rank}, final_score={self.final_score:.4f})>")
