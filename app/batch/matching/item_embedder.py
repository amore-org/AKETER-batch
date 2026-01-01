"""아이템 임베딩 생성"""
from typing import Dict, List, Tuple
import logging
import numpy as np
from sqlalchemy.orm import Session

from ...models import ItemFeature
from ...utils.embedding_client import EmbeddingClient

logger = logging.getLogger(__name__)


class ItemEmbedder:
    """아이템 임베딩 생성 클래스"""

    def __init__(self, embedding_client: EmbeddingClient):
        """ItemEmbedder 초기화

        Args:
            embedding_client: 임베딩 클라이언트
        """
        self.embedding_client = embedding_client

    def generate_all_item_embeddings(
        self,
        db: Session,
        batch_size: int = 100
    ) -> Dict[int, np.ndarray]:
        """모든 아이템 임베딩 생성 (배치 처리)

        Args:
            db: 데이터베이스 세션
            batch_size: 배치 크기

        Returns:
            {item_id: embedding} 딕셔너리
        """
        # 모든 아이템 조회
        items = db.query(ItemFeature).all()

        if not items:
            logger.warning("ItemFeature 테이블에 데이터 없음")
            return {}

        logger.info(f"{len(items)}개 아이템 임베딩 생성 시작 (batch_size={batch_size})")

        # 컨텍스트 생성
        item_ids = []
        contexts = []

        for item in items:
            item_ids.append(item.item_id)
            context = self._build_item_context(item)
            contexts.append(context)

        # 배치 임베딩 생성
        embeddings = self.embedding_client.embed_batch(
            contexts,
            batch_size=batch_size,
            show_progress=True
        )

        # 딕셔너리로 변환
        item_embeddings = {
            item_id: embedding
            for item_id, embedding in zip(item_ids, embeddings)
        }

        logger.info(f"아이템 임베딩 생성 완료: {len(item_embeddings)}개")

        return item_embeddings

    def generate_item_embedding(
        self,
        db: Session,
        item_id: int
    ) -> np.ndarray:
        """단일 아이템 임베딩 생성

        Args:
            db: 데이터베이스 세션
            item_id: 아이템 ID

        Returns:
            임베딩 벡터

        Raises:
            ValueError: 아이템이 존재하지 않는 경우
        """
        item = db.query(ItemFeature).filter(ItemFeature.item_id == item_id).first()

        if not item:
            raise ValueError(f"아이템 {item_id} 존재하지 않음")

        context = self._build_item_context(item)
        embedding = self.embedding_client.embed_text(context)

        logger.info(f"아이템 {item_id} 임베딩 생성 완료")

        return embedding

    def _build_item_context(self, item: ItemFeature) -> str:
        """아이템 데이터를 임베딩용 컨텍스트로 변환

        Context 형식:
            타겟연령대=20-30대 카테고리=SKINCARE 성분=히알루론산,나이아신아마이드
            USP=48시간지속수분 가격포지션=VALUE 프로모션타입=EVENT
            [profile_text]

        Args:
            item: ItemFeature 객체

        Returns:
            "key=value" 형식의 컨텍스트 텍스트 + profile_text
        """
        parts = []

        # 1. target_age_segment
        if item.target_age_segment:
            parts.append(f"타겟연령대={item.target_age_segment}")

        # 2. primary_category (Enum)
        if item.primary_category:
            parts.append(f"카테고리={item.primary_category.value}")

        # 3. ingredients_doc
        if item.ingredients_doc:
            parts.append(f"성분={item.ingredients_doc}")

        # 4. usp_doc
        if item.usp_doc:
            parts.append(f"USP={item.usp_doc}")

        # 5. price_position (Enum)
        if item.price_position:
            parts.append(f"가격포지션={item.price_position.value}")

        # 6. promotion_type (Enum)
        if item.promotion_type:
            parts.append(f"프로모션타입={item.promotion_type.value}")

        # 7. profile_text 추가
        context = " ".join(parts)

        if item.profile_text and item.profile_text.strip():
            context = f"{context} {item.profile_text.strip()}"

        logger.debug(f"아이템 {item.item_id} 컨텍스트: {context[:100]}...")

        return context
