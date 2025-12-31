from sqlalchemy import Column, BigInteger, String, Date, Integer, Float, Enum as SQLEnum, DateTime, ForeignKey
from datetime import datetime

from .base import Base
from .user_feature import (
    PriceSensitivityEnum,
    BenefitSensitivityEnum,
    BrandLoyaltyEnum,
    PurchaseStyleEnum
)


class PersonaRepresentativeFeature(Base):
    __tablename__ = "persona_representative_feature"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    persona_id = Column(BigInteger, ForeignKey("persona.id"), nullable=False, index=True)
    sample_rank = Column(Integer, nullable=False)  # 1, 2, 3
    sample_label = Column(String(50), nullable=True)
    as_of_date = Column(Date, nullable=False, index=True)

    # 범주형
    age_band = Column(String(20), nullable=True)
    primary_category = Column(String(30), nullable=True)
    core_keyword = Column(String(80), nullable=True)
    trend_keyword = Column(String(80), nullable=True)

    # Enum
    price_sensitivity = Column(SQLEnum(PriceSensitivityEnum), nullable=True)
    benefit_sensitivity = Column(SQLEnum(BenefitSensitivityEnum), nullable=True)
    brand_loyalty = Column(SQLEnum(BrandLoyaltyEnum), nullable=True)
    purchase_style = Column(SQLEnum(PurchaseStyleEnum), nullable=True)

    # 수치형
    price_sensitivity_score = Column(Float, nullable=True)
    benefit_sensitivity_score = Column(Float, nullable=True)
    brand_loyalty_score = Column(Float, nullable=True)

    # 타임스탬프
    created_at = Column(DateTime(6), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(6), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PersonaRepresentativeFeature(persona_id={self.persona_id}, sample_rank={self.sample_rank}, as_of_date={self.as_of_date})>"
