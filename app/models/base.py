"""SQLAlchemy Base 정의"""
from sqlalchemy.ext.declarative import declarative_base

# 모든 모델이 공유하는 Base
Base = declarative_base()
