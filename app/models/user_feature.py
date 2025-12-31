from sqlalchemy import Column, BigInteger, String, Date, Float, Enum as SQLEnum, DateTime, ForeignKey
from datetime import datetime
import enum

from .base import Base


class PriceSensitivityEnum(str, enum.Enum):
    """가격 민감도"""
    DISCOUNT_APPLIED_PRODUCT = "DISCOUNT_APPLIED_PRODUCT"
    PREMIUM = "PREMIUM"
    VALUE = "VALUE"


class BenefitSensitivityEnum(str, enum.Enum):
    """혜택 민감도"""
    EVENT = "EVENT"
    FREE_GIFT = "FREE_GIFT"
    SEASON_PROMO = "SEASON_PROMO"


class BrandLoyaltyEnum(str, enum.Enum):
    """브랜드 충성도"""
    CATEGORY_SPLIT_BY_BRAND = "CATEGORY_SPLIT_BY_BRAND"
    MULTI_BRAND_MIX = "MULTI_BRAND_MIX"
    NEW_PRODUCT_EXPLORER = "NEW_PRODUCT_EXPLORER"
    SINGLE_BRAND_LOYAL = "SINGLE_BRAND_LOYAL"


class PurchaseStyleEnum(str, enum.Enum):
    """구매 스타일"""
    CART_HOLD_THEN_BUY = "CART_HOLD_THEN_BUY"
    COMPARE_THEN_BUY = "COMPARE_THEN_BUY"
    INSTANT_BUY = "INSTANT_BUY"
    REBUY_AFTER_CONSUME = "REBUY_AFTER_CONSUME"
    WAIT_PROMO = "WAIT_PROMO"


class UserFeature(Base):
    """유저 피처 테이블"""
    __tablename__ = "user_feature"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, unique=True, index=True)
    persona_id = Column(BigInteger, ForeignKey("persona.id"), nullable=True, index=True)

    # 스냅샷 기준일
    as_of_date = Column(Date, nullable=False, index=True)

    # 범주형 피처
    age_band = Column(String(20), nullable=True)
    primary_category = Column(String(30), nullable=True)
    core_keyword = Column(String(80), nullable=True)
    trend_keyword = Column(String(80), nullable=True)

    # Enum 피처
    price_sensitivity = Column(SQLEnum(PriceSensitivityEnum), nullable=True)
    benefit_sensitivity = Column(SQLEnum(BenefitSensitivityEnum), nullable=True)
    brand_loyalty = Column(SQLEnum(BrandLoyaltyEnum), nullable=True)
    purchase_style = Column(SQLEnum(PurchaseStyleEnum), nullable=True)

    # 수치형 피처 (0~1 범위)
    price_sensitivity_score = Column(Float, nullable=True)
    benefit_sensitivity_score = Column(Float, nullable=True)
    brand_loyalty_score = Column(Float, nullable=True)

    # 타임스탬프
    created_at = Column(DateTime(6), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(6), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<UserFeature(user_id={self.user_id}, persona_id={self.persona_id}, as_of_date={self.as_of_date})>"
