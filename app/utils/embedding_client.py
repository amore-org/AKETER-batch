"""텍스트 임베딩 클라이언트"""
from typing import List, Union
import logging
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """SentenceTransformer를 사용한 텍스트 임베딩 클라이언트"""

    def __init__(self, model_name: str):
        """임베딩 클라이언트 초기화

        Args:
            model_name: SentenceTransformer 모델명
                예: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        """
        self.model_name = model_name
        logger.info(f"임베딩 모델 로드 중: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"임베딩 모델 로드 완료: 차원={self.embedding_dim}")

    def embed_text(self, text: str) -> np.ndarray:
        """단일 텍스트를 임베딩 벡터로 변환

        Args:
            text: 임베딩할 텍스트

        Returns:
            numpy array 형태의 임베딩 벡터
        """
        if not text or not text.strip():
            logger.warning("빈 텍스트 입력 - 제로 벡터 반환")
            return np.zeros(self.embedding_dim, dtype=np.float32)

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """여러 텍스트를 배치로 임베딩

        Args:
            texts: 임베딩할 텍스트 리스트
            batch_size: 배치 크기
            show_progress: 진행률 표시 여부

        Returns:
            (len(texts), embedding_dim) 형태의 numpy array
        """
        if not texts:
            logger.warning("빈 텍스트 리스트 - 빈 배열 반환")
            return np.array([]).reshape(0, self.embedding_dim)

        logger.info(f"배치 임베딩 시작: {len(texts)}개 텍스트, batch_size={batch_size}")

        # 빈 텍스트를 공백으로 대체 (SentenceTransformer는 빈 문자열 처리 못함)
        processed_texts = [text.strip() if text and text.strip() else " " for text in texts]

        embeddings = self.model.encode(
            processed_texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )

        logger.info(f"배치 임베딩 완료: shape={embeddings.shape}")
        return embeddings

    def compute_similarity(
        self,
        embedding1: Union[np.ndarray, List[float]],
        embedding2: Union[np.ndarray, List[float]]
    ) -> float:
        """두 임베딩 벡터 간 코사인 유사도 계산

        Args:
            embedding1: 첫 번째 임베딩 벡터
            embedding2: 두 번째 임베딩 벡터

        Returns:
            코사인 유사도 (0.0 ~ 1.0)
        """
        emb1 = np.array(embedding1)
        emb2 = np.array(embedding2)

        # 제로 벡터 처리
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            logger.warning("제로 벡터 감지 - 유사도 0.0 반환")
            return 0.0

        # 코사인 유사도 계산
        similarity = np.dot(emb1, emb2) / (norm1 * norm2)

        # -1 ~ 1 범위를 0 ~ 1로 정규화
        normalized_similarity = (similarity + 1) / 2

        return float(normalized_similarity)

    def get_embedding_dimension(self) -> int:
        """임베딩 벡터의 차원 반환

        Returns:
            임베딩 차원
        """
        return self.embedding_dim
