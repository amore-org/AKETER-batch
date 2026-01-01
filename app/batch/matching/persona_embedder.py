"""페르소나 임베딩 생성"""
from typing import Dict, List, Optional
from datetime import date
import logging
import numpy as np
from sqlalchemy.orm import Session

from ...models import PersonaRepresentativeFeature
from ...utils.embedding_client import EmbeddingClient

logger = logging.getLogger(__name__)


class PersonaEmbedder:
    """페르소나 임베딩 생성 클래스"""

    def __init__(self, embedding_client: EmbeddingClient):
        """PersonaEmbedder 초기화

        Args:
            embedding_client: 임베딩 클라이언트
        """
        self.embedding_client = embedding_client

    def generate_persona_embedding(
        self,
        db: Session,
        persona_id: int,
        as_of_date: date
    ) -> Optional[np.ndarray]:
        """페르소나 임베딩 생성 (대표자 3명 평균)

        Args:
            db: 데이터베이스 세션
            persona_id: 페르소나 ID
            as_of_date: 기준일

        Returns:
            평균 임베딩 벡터 (대표자가 없으면 None)
        """
        # 대표자 3명 조회
        representatives = db.query(PersonaRepresentativeFeature).filter(
            PersonaRepresentativeFeature.persona_id == persona_id,
            PersonaRepresentativeFeature.as_of_date == as_of_date
        ).order_by(PersonaRepresentativeFeature.sample_rank).all()

        if not representatives:
            logger.warning(f"Persona {persona_id}: 대표자 데이터 없음 - 임베딩 생성 스킵")
            return None

        logger.info(f"Persona {persona_id}: 대표자 {len(representatives)}명 컨텍스트 생성")

        # 각 대표자의 컨텍스트 생성 및 임베딩
        embeddings = []
        for rep in representatives:
            context = self._build_representative_context(rep)
            embedding = self.embedding_client.embed_text(context)
            embeddings.append(embedding)

        # 평균 벡터 계산
        avg_embedding = np.mean(embeddings, axis=0)

        logger.info(
            f"Persona {persona_id} 임베딩 생성 완료: "
            f"{len(representatives)}명 평균, shape={avg_embedding.shape}"
        )

        return avg_embedding

    def generate_all_persona_embeddings(
        self,
        db: Session,
        persona_ids: List[int],
        as_of_date: date
    ) -> Dict[int, np.ndarray]:
        """모든 페르소나 임베딩 생성

        Args:
            db: 데이터베이스 세션
            persona_ids: 페르소나 ID 리스트
            as_of_date: 기준일

        Returns:
            {persona_id: embedding} 딕셔너리
        """
        logger.info(f"{len(persona_ids)}개 페르소나 임베딩 생성 시작")

        persona_embeddings = {}

        for persona_id in persona_ids:
            embedding = self.generate_persona_embedding(db, persona_id, as_of_date)

            if embedding is not None:
                persona_embeddings[persona_id] = embedding
            else:
                logger.warning(f"Persona {persona_id}: 임베딩 생성 실패 - 스킵")

        logger.info(
            f"페르소나 임베딩 생성 완료: "
            f"{len(persona_embeddings)}/{len(persona_ids)}개 성공"
        )

        return persona_embeddings

    def _build_representative_context(self, rep: PersonaRepresentativeFeature) -> str:
        """대표자 데이터를 임베딩용 컨텍스트로 변환

        Args:
            rep: PersonaRepresentativeFeature 객체

        Returns:
            "key=value" 형식의 컨텍스트 텍스트
        """
        parts = []

        # 범주형 필드
        if rep.age_band:
            parts.append(f"연령대={rep.age_band}")

        if rep.primary_category:
            parts.append(f"카테고리={rep.primary_category}")

        if rep.core_keyword:
            parts.append(f"핵심키워드={rep.core_keyword}")

        if rep.trend_keyword:
            parts.append(f"트렌드키워드={rep.trend_keyword}")

        # Enum 필드
        if rep.price_sensitivity:
            parts.append(f"가격민감도={rep.price_sensitivity.value}")

        if rep.benefit_sensitivity:
            parts.append(f"혜택민감도={rep.benefit_sensitivity.value}")

        if rep.brand_loyalty:
            parts.append(f"브랜드충성도={rep.brand_loyalty.value}")

        if rep.purchase_style:
            parts.append(f"구매스타일={rep.purchase_style.value}")

        context = " ".join(parts)

        logger.debug(f"대표자 {rep.sample_rank} 컨텍스트: {context[:100]}...")

        return context
