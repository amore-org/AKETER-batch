"""사용자-아이템 상호작용 집계 모델"""
from sqlalchemy import Column, BigInteger, Boolean, Date, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime

from .base import Base


class UserItemInteraction(Base):
    """사용자-아이템 상호작용 집계 테이블"""
    __tablename__ = "user_item_interaction"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Keys
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(BigInteger, ForeignKey("item.id"), nullable=False, index=True)

    # 상호작용 집계
    click_cnt = Column(BigInteger, nullable=False, default=0)
    purchase_cnt = Column(BigInteger, nullable=False, default=0)
    is_in_cart = Column(Boolean, nullable=False, default=False)
    is_wishlisted = Column(Boolean, nullable=False, default=False)

    # 날짜 정보
    as_of_date = Column(Date, nullable=False)
    last_interaction_at = Column(DateTime(6), nullable=True)

    # 타임스탬프
    created_at = Column(DateTime(6), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(6), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Unique Constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'item_id', name='uk_uii_user_item'),
    )

    def __repr__(self):
        return (f"<UserItemInteraction(user_id={self.user_id}, item_id={self.item_id}, "
                f"clicks={self.click_cnt}, purchases={self.purchase_cnt})>")
