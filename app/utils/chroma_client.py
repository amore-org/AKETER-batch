"""ChromaDB 벡터 데이터베이스 클라이언트"""
from typing import List, Dict, Any, Optional
import logging
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class ChromaClient:
    """ChromaDB 벡터 데이터베이스 클라이언트"""

    def __init__(self, host: str = "localhost", port: int = 8000):
        """ChromaDB 클라이언트 초기화

        Args:
            host: ChromaDB 서버 호스트
            port: ChromaDB 서버 포트
        """
        self.host = host
        self.port = port
        logger.info(f"ChromaDB 초기화: host={host}, port={port}")

        # HttpClient 생성 (ChromaDB 서버 연결)
        self.client = chromadb.HttpClient(
            host=host,
            port=port,
            settings=Settings(
                anonymized_telemetry=False,
            )
        )

        logger.info("ChromaDB 클라이언트 초기화 완료")

    def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> chromadb.Collection:
        """컬렉션 조회 또는 생성

        Args:
            name: 컬렉션 이름 (예: "personas", "items")
            metadata: 컬렉션 메타데이터 (선택)

        Returns:
            ChromaDB Collection 객체
        """
        try:
            # ChromaDB는 빈 딕셔너리를 허용하지 않으므로
            # metadata가 None이면 파라미터 자체를 전달하지 않음
            if metadata:
                collection = self.client.get_or_create_collection(
                    name=name,
                    metadata=metadata
                )
            else:
                collection = self.client.get_or_create_collection(
                    name=name
                )
            logger.info(f"컬렉션 '{name}' 준비 완료 (항목 수: {collection.count()})")
            return collection

        except Exception as e:
            logger.error(f"컬렉션 '{name}' 생성 실패: {e}", exc_info=True)
            raise

    def add_embeddings(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None
    ) -> None:
        """컬렉션에 임베딩 추가 (upsert 방식)

        Args:
            collection_name: 컬렉션 이름
            ids: 임베딩 ID 리스트 (중복 시 덮어쓰기)
            embeddings: 임베딩 벡터 리스트
            metadatas: 메타데이터 리스트 (선택)
            documents: 원본 텍스트 리스트 (선택)
        """
        if not ids or not embeddings:
            logger.warning(f"빈 데이터 입력 - 컬렉션 '{collection_name}'에 추가 스킵")
            return

        if len(ids) != len(embeddings):
            raise ValueError(f"IDs와 embeddings 개수 불일치: {len(ids)} vs {len(embeddings)}")

        try:
            collection = self.get_or_create_collection(collection_name)

            # Upsert: 기존 ID는 업데이트, 신규 ID는 추가
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )

            logger.info(
                f"컬렉션 '{collection_name}'에 {len(ids)}개 임베딩 추가/업데이트 완료 "
                f"(전체: {collection.count()})"
            )

        except Exception as e:
            logger.error(
                f"컬렉션 '{collection_name}'에 임베딩 추가 실패: {e}",
                exc_info=True
            )
            raise

    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """유사 벡터 검색 (코사인 유사도)

        Args:
            collection_name: 컬렉션 이름
            query_embedding: 쿼리 임베딩 벡터
            n_results: 반환할 결과 개수
            where: 메타데이터 필터 (선택)

        Returns:
            검색 결과 딕셔너리
            {
                'ids': [[id1, id2, ...]],
                'distances': [[dist1, dist2, ...]],  # 낮을수록 유사
                'metadatas': [[meta1, meta2, ...]],
                'documents': [[doc1, doc2, ...]]
            }
        """
        try:
            collection = self.get_or_create_collection(collection_name)

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )

            logger.debug(
                f"컬렉션 '{collection_name}' 검색 완료: "
                f"{len(results['ids'][0]) if results['ids'] else 0}개 결과"
            )

            return results

        except Exception as e:
            logger.error(
                f"컬렉션 '{collection_name}' 검색 실패: {e}",
                exc_info=True
            )
            raise

    def delete_collection(self, name: str) -> None:
        """컬렉션 삭제

        Args:
            name: 컬렉션 이름
        """
        try:
            self.client.delete_collection(name=name)
            logger.info(f"컬렉션 '{name}' 삭제 완료")

        except Exception as e:
            logger.warning(f"컬렉션 '{name}' 삭제 실패: {e}")

    def reset(self) -> None:
        """모든 컬렉션 삭제"""
        logger.warning("ChromaDB 전체 리셋 수행")
        self.client.reset()
        logger.info("ChromaDB 리셋 완료")

    def list_collections(self) -> List[str]:
        """모든 컬렉션 이름 조회

        Returns:
            컬렉션 이름 리스트
        """
        collections = self.client.list_collections()
        collection_names = [c.name for c in collections]
        logger.info(f"컬렉션 목록: {collection_names}")
        return collection_names
