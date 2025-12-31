import logging
import numpy as np
from typing import Dict, List, Tuple


logger = logging.getLogger(__name__)


class RepresentativeSelector:
    """페르소나 대표자 선정

    각 군집의 centroid와 가장 가까운 N명을 대표자로 선정합니다.
    """

    def __init__(self, n_representatives: int = 3):
        """
        Args:
            n_representatives: 군집당 대표자 수
        """
        self.n_representatives = n_representatives

    def select_representatives(
        self,
        X: np.ndarray,
        labels: np.ndarray,
        user_ids: np.ndarray
    ) -> Dict[int, List[Tuple[int, int, float]]]:
        """각 군집별 대표자 선정

        Args:
            X: 전처리된 피처 행렬 (n_samples, n_features)
            labels: 클러스터 레이블 (n_samples,)
            user_ids: 유저 ID 배열 (n_samples,)

        Returns:
            {persona_id: [(user_id, rank, distance), ...]} 딕셔너리
            rank는 1부터 시작 (1이 가장 가까움)
        """
        logger.info(f"대표자 선정 시작 - 군집당 {self.n_representatives}명")

        representatives = {}
        unique_labels = np.unique(labels)

        for cluster_id in unique_labels:
            # 해당 군집의 데이터 포인트 추출
            cluster_mask = labels == cluster_id
            cluster_points = X[cluster_mask]
            cluster_user_ids = user_ids[cluster_mask]

            # 군집 크기 체크
            if len(cluster_points) < self.n_representatives:
                logger.warning(
                    f"군집 {cluster_id}의 크기({len(cluster_points)})가 "
                    f"대표자 수({self.n_representatives})보다 작습니다."
                )
                n_reps = len(cluster_points)
            else:
                n_reps = self.n_representatives

            # Centroid 계산
            centroid = cluster_points.mean(axis=0)

            # Centroid와의 유클리드 거리 계산
            distances = np.linalg.norm(cluster_points - centroid, axis=1)

            # 가장 가까운 N명 선정
            nearest_indices = np.argsort(distances)[:n_reps]

            # 대표자 정보 저장 (user_id, rank, distance)
            representatives[int(cluster_id)] = [
                (
                    int(cluster_user_ids[idx]),
                    rank + 1,  # rank는 1부터 시작
                    float(distances[idx])
                )
                for rank, idx in enumerate(nearest_indices)
            ]

            logger.info(
                f"군집 {cluster_id}: {len(representatives[int(cluster_id)])}명 선정"
            )

        logger.info(f"대표자 선정 완료 - 총 {len(representatives)}개 군집")

        return representatives

    def get_representative_user_ids(
        self,
        representatives: Dict[int, List[Tuple[int, int, float]]]
    ) -> List[int]:
        """모든 대표자의 user_id 리스트 반환

        Args:
            representatives: select_representatives() 결과

        Returns:
            대표자 user_id 리스트
        """
        user_ids = []
        for cluster_id, reps in representatives.items():
            for user_id, rank, distance in reps:
                user_ids.append(user_id)

        return user_ids
