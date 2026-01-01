"""아이템 피처 모델"""
from sqlalchemy import Column, BigInteger, String, Integer, Float, Enum as SQLEnum, DateTime, ForeignKey, Text
from datetime import datetime
import enum

from .base import Base


class PrimaryCategoryEnum(str, enum.Enum):
    """제품 주요 카테고리"""
    BODY = "BODY"
    CLEANSING = "CLEANSING"
    HAIR = "HAIR"
    MAKEUP = "MAKEUP"
    MEN = "MEN"
    OTHER = "OTHER"
    PERFUME = "PERFUME"
    SKINCARE = "SKINCARE"
    SUNCARE = "SUNCARE"


class PricePositionEnum(str, enum.Enum):
    """가격 포지션"""
    DISCOUNT_APPLIED_PRODUCT = "DISCOUNT_APPLIED_PRODUCT"
    PREMIUM = "PREMIUM"
    VALUE = "VALUE"


class PromotionTypeEnum(str, enum.Enum):
    """프로모션 타입"""
    EVENT = "EVENT"
    FREE_GIFT = "FREE_GIFT"
    SEASON_PROMO = "SEASON_PROMO"


class ItemFeature(Base):
    """아이템 피처 테이블"""
    __tablename__ = "item_feature"

    # Primary Key
    item_id = Column(BigInteger, ForeignKey("item.id"), primary_key=True, nullable=False)

    # 제품 정보
    item_name = Column(String(200), nullable=False)
    meta_path = Column(String(500), nullable=False)

    # 타겟 연령대
    target_age_segment = Column(String(20), nullable=True)
    target_age_min = Column(Integer, nullable=True)
    target_age_max = Column(Integer, nullable=True)

    # 카테고리 및 포지셔닝
    primary_category = Column(SQLEnum(PrimaryCategoryEnum), nullable=True)
    price_position = Column(SQLEnum(PricePositionEnum), nullable=True)
    promotion_type = Column(SQLEnum(PromotionTypeEnum), nullable=True)

    # 제품 설명 문서
    ingredients_doc = Column(String(500), nullable=True)
    ingredients_doc_path = Column(String(500), nullable=True)
    usp_doc = Column(String(500), nullable=True)
    usp_doc_path = Column(String(500), nullable=True)

    # 프로필 텍스트
    profile_text = Column(Text, nullable=True)

    # 판매 선호도 점수
    sales_preference_score = Column(Float, nullable=True)

    # 타임스탬프
    created_at = Column(DateTime(6), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(6), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ItemFeature(item_id={self.item_id}, name='{self.item_name}', category={self.primary_category})>"
