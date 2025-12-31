import logging
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from typing import Dict, Tuple


logger = logging.getLogger(__name__)


class PersonaClusterer:
    """KMeans 기반 페르소나 클러스터링"""

    def __init__(self, n_clusters: int = 8, random_state: int = 42):
        """
        Args:
            n_clusters: 페르소나 군집 수
            random_state: 난수 시드 (재현성)
        """
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=random_state,
            n_init=10,  # 여러 초기화 시도
            max_iter=300,
            algorithm='lloyd'
        )
        self.labels_ = None
        self.cluster_centers_ = None

    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        """클러스터링 수행 및 레이블 반환

        Args:
            X: 전처리된 피처 행렬 (n_samples, n_features)

        Returns:
            클러스터 레이블 배열 (n_samples,)
        """
        logger.info(f"KMeans 클러스터링 시작 - n_clusters={self.n_clusters}")

        self.labels_ = self.kmeans.fit_predict(X)
        self.cluster_centers_ = self.kmeans.cluster_centers_

        logger.info(f"KMeans 수렴 완료 - 반복 횟수: {self.kmeans.n_iter_}")

        return self.labels_

    def get_cluster_centers(self) -> np.ndarray:
        """군집 중심점 반환

        Returns:
            군집 중심점 배열 (n_clusters, n_features)
        """
        if self.cluster_centers_ is None:
            raise ValueError("클러스터링이 아직 수행되지 않았습니다. fit_predict()를 먼저 호출하세요.")

        return self.cluster_centers_

    def evaluate(self, X: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
        """클러스터링 품질 평가

        Args:
            X: 전처리된 피처 행렬
            labels: 클러스터 레이블

        Returns:
            평가 지표 딕셔너리
        """
        # 클러스터 수가 2개 이상일 때만 평가 가능
        if self.n_clusters < 2:
            logger.warning("클러스터 수가 2 미만이므로 평가를 건너뜁니다.")
            return {}

        # 실루엣 스코어 (높을수록 좋음, -1~1)
        silhouette = silhouette_score(X, labels)

        # Davies-Bouldin Index (낮을수록 좋음, 0 이상)
        davies_bouldin = davies_bouldin_score(X, labels)

        # Calinski-Harabasz Index (높을수록 좋음, 0 이상)
        calinski_harabasz = calinski_harabasz_score(X, labels)

        # Inertia (관성, 낮을수록 좋음)
        inertia = self.kmeans.inertia_

        metrics = {
            'silhouette_score': float(silhouette),
            'davies_bouldin_index': float(davies_bouldin),
            'calinski_harabasz_score': float(calinski_harabasz),
            'inertia': float(inertia)
        }

        logger.info(f"클러스터링 평가 지표: {metrics}")

        return metrics

    def get_cluster_sizes(self, labels: np.ndarray) -> Dict[int, int]:
        """각 군집별 멤버 수 반환

        Args:
            labels: 클러스터 레이블

        Returns:
            {cluster_id: count} 딕셔너리
        """
        unique, counts = np.unique(labels, return_counts=True)
        cluster_sizes = dict(zip(unique.tolist(), counts.tolist()))

        logger.info(f"군집별 멤버 수: {cluster_sizes}")

        return cluster_sizes
