"""협업 필터링 기반 아이템 추천"""
from typing import List, Tuple, Dict
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func

from ...models import UserFeature, UserItemInteraction

logger = logging.getLogger(__name__)


class CollaborativeFilter:
    """협업 필터링 추천 클래스"""

    # 행동 타입별 가중치
    WEIGHTS = {
        'purchase': 3.0,  # 구매
        'cart': 2.0,      # 장바구니
        'wish': 2.0,      # 찜하기
        'click': 1.0      # 클릭
    }

    def __init__(self):
        """CollaborativeFilter 초기화"""
        pass

    def calculate_cf_scores(
        self,
        db: Session,
        persona_id: int,
        top_n: int = 5
    ) -> List[Tuple[int, float]]:
        """페르소나 기반 협업 필터링 점수 계산

        Args:
            db: 데이터베이스 세션
            persona_id: 페르소나 ID
            top_n: 반환할 아이템 개수

        Returns:
            [(item_id, cf_score), ...] 리스트 (내림차순)
        """
        # 1. 페르소나 소속 유저 조회
        user_ids = self._get_persona_users(db, persona_id)

        if not user_ids:
            logger.warning(f"Persona {persona_id}: 소속 유저 없음 - CF 스킵")
            return []

        logger.info(f"Persona {persona_id}: {len(user_ids)}명 유저의 행동 로그 집계")

        # 2. 행동 로그 집계 및 가중치 적용
        item_scores = self._aggregate_interactions(db, user_ids)

        if not item_scores:
            logger.warning(f"Persona {persona_id}: 행동 로그 없음 - CF 스킵")
            return []

        # 3. Min-Max 정규화
        normalized_scores = self._normalize_scores(item_scores)

        # 4. Top N 추출
        top_items = sorted(normalized_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

        logger.info(
            f"Persona {persona_id} CF 완료: "
            f"{len(item_scores)}개 아이템 → Top {len(top_items)}"
        )

        return top_items

    def _get_persona_users(self, db: Session, persona_id: int) -> List[int]:
        """페르소나에 속한 유저 ID 조회

        Args:
            db: 데이터베이스 세션
            persona_id: 페르소나 ID

        Returns:
            유저 ID 리스트
        """
        users = db.query(UserFeature.user_id).filter(
            UserFeature.persona_id == persona_id
        ).all()

        user_ids = [user.user_id for user in users]

        logger.debug(f"Persona {persona_id}: {len(user_ids)}명 유저 조회")

        return user_ids

    def _aggregate_interactions(
        self,
        db: Session,
        user_ids: List[int]
    ) -> Dict[int, float]:
        """사용자-아이템 상호작용 집계 및 가중치 적용

        Args:
            db: 데이터베이스 세션
            user_ids: 유저 ID 리스트

        Returns:
            {item_id: raw_score} 딕셔너리
        """
        # 사용자들의 상호작용 데이터 조회
        interactions = db.query(UserItemInteraction).filter(
            UserItemInteraction.user_id.in_(user_ids)
        ).all()

        # 아이템별 가중치 점수 계산
        item_scores = {}

        for interaction in interactions:
            item_id = interaction.item_id
            score = 0.0

            # 각 행동에 대해 가중치 적용
            score += interaction.purchase_cnt * self.WEIGHTS['purchase']
            score += (1 if interaction.is_in_cart else 0) * self.WEIGHTS['cart']
            score += (1 if interaction.is_wishlisted else 0) * self.WEIGHTS['wish']
            score += interaction.click_cnt * self.WEIGHTS['click']

            if item_id in item_scores:
                item_scores[item_id] += score
            else:
                item_scores[item_id] = score

        logger.debug(
            f"상호작용 집계 완료: "
            f"{len(interactions)}개 레코드 → {len(item_scores)}개 아이템"
        )

        return item_scores

    def _normalize_scores(self, item_scores: Dict[int, float]) -> Dict[int, float]:
        """Min-Max 정규화 (0~1 범위)

        Args:
            item_scores: {item_id: raw_score}

        Returns:
            {item_id: normalized_score}
        """
        if not item_scores:
            return {}

        scores = list(item_scores.values())
        min_score = min(scores)
        max_score = max(scores)

        # 모든 점수가 동일한 경우
        if max_score == min_score:
            logger.warning("모든 CF 점수가 동일 - 1.0으로 정규화")
            return {item_id: 1.0 for item_id in item_scores.keys()}

        # Min-Max 정규화
        normalized = {
            item_id: (score - min_score) / (max_score - min_score)
            for item_id, score in item_scores.items()
        }

        logger.debug(
            f"점수 정규화 완료: "
            f"원본 범위 [{min_score:.2f}, {max_score:.2f}] → [0.0, 1.0]"
        )

        return normalized
