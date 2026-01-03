from datetime import date, datetime, timedelta
import logging
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Tuple

from app.database import SessionLocal
from app.models import User, UserFeature, Persona, PersonaRepresentativeFeature, PersonaItem, ItemFeature
from app.batch.clustering import FeaturePreprocessor, PersonaClusterer, RepresentativeSelector
from app.utils.llm_client import LLMClient
from app.utils.embedding_client import EmbeddingClient
from app.utils.chroma_client import ChromaClient
from app.batch.matching import PersonaEmbedder, ItemEmbedder, CollaborativeFilter
from app.config import get_settings


logger = logging.getLogger(__name__)


class PersonaClusteringTask:
    """페르소나 클러스터링 배치 작업

    1. user_feature 데이터 로드
    2. 데이터 전처리 (TopN+OTHER, 인코딩, 스케일링)
    3. KMeans 클러스터링 수행
    4. user_feature.persona_id 업데이트
    5. 대표자 선정 및 persona_representative_feature 저장
    6. persona.member_count 업데이트
    """

    def __init__(
        self,
        as_of_date: str = None,
        n_clusters: int = 8,
        top_n: int = 10
    ):
        """
        Args:
            as_of_date: 스냅샷 기준일 (YYYY-MM-DD), None이면 전날 사용
            n_clusters: 페르소나 군집 수
            top_n: TopN 범주 수
        """
        if as_of_date is None:
            # 기본값: 실행일 전날
            self.as_of_date = (date.today() - timedelta(days=1)).isoformat()
        else:
            self.as_of_date = as_of_date

        self.n_clusters = n_clusters
        self.top_n = top_n

    def execute(self) -> Dict[str, Any]:
        """배치 작업 실행

        Returns:
            실행 결과 딕셔너리
        """
        logger.info(f"=== 페르소나 클러스터링 시작 ===")
        logger.info(f"as_of_date: {self.as_of_date}")
        logger.info(f"n_clusters: {self.n_clusters}")
        logger.info(f"top_n: {self.top_n}")

        db = SessionLocal()

        try:
            # 1단계: 데이터 로드
            df = self._load_user_features(db)

            if len(df) == 0:
                logger.warning(f"as_of_date={self.as_of_date}에 해당하는 데이터가 없습니다.")
                return {
                    'status': 'no_data',
                    'as_of_date': self.as_of_date,
                    'message': '처리할 데이터가 없습니다.'
                }

            logger.info(f"로드된 유저 수: {len(df)}")

            # 2단계: 전처리
            X, user_ids, preprocessor = self._preprocess_data(df)
            logger.info(f"전처리 완료 - 피처 차원: {X.shape}")

            # 3단계: 클러스터링
            labels, metrics = self._run_clustering(X)
            logger.info(f"클러스터링 완료")

            # 3.5단계: persona 테이블 레코드 생성 (FK 제약조건 해결)
            self._create_or_update_personas(db, labels)
            logger.info("persona 테이블 레코드 생성 완료")

            # 4단계: persona_id 업데이트
            self._update_persona_ids(db, user_ids, labels)
            logger.info("persona_id 업데이트 완료")

            # 5단계: 대표자 선정 및 저장
            representatives = self._select_and_save_representatives(
                db, df, X, labels, user_ids
            )
            logger.info(f"대표자 선정 완료 - {len(representatives)}개 군집")

            # 6단계: persona 테이블 member_count 업데이트
            self._update_persona_member_counts(db, labels)
            logger.info("persona.member_count 업데이트 완료")

            # 7단계: LLM 프로필 생성 (NEW)
            profiles_generated = 0
            try:
                profiles = self._generate_persona_profiles(db)

                # 7.5단계: 프로필 DB 업데이트
                if profiles:
                    self._update_persona_profiles(db, profiles)
                    profiles_generated = len(profiles)
                    logger.info(f"LLM 프로필 생성 및 업데이트 완료 ({profiles_generated}개)")
                else:
                    logger.warning("생성된 프로필이 없습니다.")

            except Exception as e:
                logger.error(
                    f"LLM 프로필 생성 실패 (배치는 계속 진행): {e}",
                    exc_info=True
                )
                # 프로필 생성 실패해도 배치는 성공 처리

            # 8단계: 페르소나-아이템 매칭 (NEW)
            interactions_saved = 0
            try:
                matching_result = self._run_item_matching(db)
                interactions_saved = matching_result.get('interactions_saved', 0)
                logger.info(
                    f"페르소나-아이템 매칭 완료: {interactions_saved}개 매칭 저장"
                )

            except Exception as e:
                logger.error(
                    f"페르소나-아이템 매칭 실패 (배치는 계속 진행): {e}",
                    exc_info=True
                )
                # 매칭 실패해도 배치는 성공 처리

            # 결과 반환
            unique, counts = np.unique(labels, return_counts=True)
            cluster_distribution = {
                int(persona_id) + 1: int(count)  # persona_id는 1부터 시작
                for persona_id, count in zip(unique, counts)
            }

            result = {
                'status': 'success',
                'as_of_date': self.as_of_date,
                'total_users': len(df),
                'n_clusters': self.n_clusters,
                'metrics': metrics,
                'cluster_distribution': cluster_distribution,
                'profiles_generated': profiles_generated,
                'interactions_saved': interactions_saved  # NEW
            }

            logger.info(f"=== 페르소나 클러스터링 완료 ===")
            logger.info(f"결과: {result}")

            db.commit()
            return result

        except Exception as e:
            logger.error(f"배치 작업 실패: {e}", exc_info=True)
            db.rollback()
            raise

        finally:
            db.close()

    def _load_user_features(self, db: Session) -> pd.DataFrame:
        """1단계: user_feature 데이터 로드 (활성 유저만)

        Args:
            db: DB 세션

        Returns:
            유저 피처 데이터프레임
        """
        query = db.query(UserFeature).join(
            User, UserFeature.user_id == User.id
        ).filter(
            UserFeature.as_of_date == self.as_of_date,
            User.is_active == True
        )

        data = []
        for row in query:
            data.append({
                'id': row.id,
                'user_id': row.user_id,
                'age_band': row.age_band,
                'primary_category': row.primary_category,
                'core_keyword': row.core_keyword,
                'trend_keyword': row.trend_keyword,
                'price_sensitivity': row.price_sensitivity.value if row.price_sensitivity else None,
                'benefit_sensitivity': row.benefit_sensitivity.value if row.benefit_sensitivity else None,
                'brand_loyalty': row.brand_loyalty.value if row.brand_loyalty else None,
                'purchase_style': row.purchase_style.value if row.purchase_style else None,
                'price_sensitivity_score': row.price_sensitivity_score,
                'benefit_sensitivity_score': row.benefit_sensitivity_score,
                'brand_loyalty_score': row.brand_loyalty_score,
            })

        df = pd.DataFrame(data)
        logger.info(f"로드 완료: {len(df)}개 레코드")

        return df

    def _preprocess_data(self, df: pd.DataFrame):
        """2단계: 데이터 전처리

        Args:
            df: 원본 데이터프레임

        Returns:
            (X, user_ids, preprocessor) 튜플
        """
        logger.info("데이터 전처리 시작")

        preprocessor = FeaturePreprocessor(top_n=self.top_n)
        X = preprocessor.fit_transform(df)
        user_ids = df['user_id'].values

        logger.info(f"전처리 완료 - 샘플 수: {X.shape[0]}, 피처 수: {X.shape[1]}")

        return X, user_ids, preprocessor

    def _run_clustering(self, X: np.ndarray):
        """3단계: 클러스터링 실행

        Args:
            X: 전처리된 피처 행렬

        Returns:
            (labels, metrics) 튜플
        """
        logger.info("KMeans 클러스터링 시작")

        clusterer = PersonaClusterer(n_clusters=self.n_clusters)
        labels = clusterer.fit_predict(X)
        metrics = clusterer.evaluate(X, labels)

        logger.info(f"클러스터링 완료 - 평가 지표: {metrics}")

        return labels, metrics

    def _create_or_update_personas(self, db: Session, labels: np.ndarray):
        """3.5단계: persona 테이블 레코드 생성 (FK 제약조건 해결)

        Args:
            db: DB 세션
            labels: 클러스터 레이블 배열
        """
        logger.info("persona 테이블 레코드 생성 시작")

        unique_persona_ids = np.unique(labels)

        for persona_id in unique_persona_ids:
            # persona_id는 1부터 시작 (KMeans는 0부터 시작하므로 +1)
            actual_persona_id = int(persona_id) + 1

            # 기존 persona 확인
            persona = db.query(Persona).filter(Persona.id == actual_persona_id).first()

            if not persona:
                # 새 persona 생성 (임시 이름)
                persona = Persona(
                    id=actual_persona_id,
                    name=f"Persona {actual_persona_id}",  # 임시 이름
                    member_count=0  # 나중에 업데이트됨
                )
                db.add(persona)
                logger.info(f"Persona {actual_persona_id} 생성")
            else:
                logger.info(f"Persona {actual_persona_id} 이미 존재")

        db.commit()
        logger.info(f"{len(unique_persona_ids)}개 페르소나 레코드 준비 완료")

    def _update_persona_ids(self, db: Session, user_ids: np.ndarray, labels: np.ndarray):
        """4단계: user_feature.persona_id 업데이트

        Args:
            db: DB 세션
            user_ids: 유저 ID 배열
            labels: 클러스터 레이블 배열
        """
        logger.info("user_feature.persona_id 업데이트 시작")

        update_count = 0
        for user_id, persona_id in zip(user_ids, labels):
            db.query(UserFeature).filter(
                UserFeature.user_id == int(user_id) + 1,
                UserFeature.as_of_date == self.as_of_date
            ).update({'persona_id': int(persona_id) + 1})
            update_count += 1

        logger.info(f"{update_count}개 레코드 업데이트 완료")

    def _select_and_save_representatives(
        self,
        db: Session,
        df: pd.DataFrame,
        X: np.ndarray,
        labels: np.ndarray,
        user_ids: np.ndarray
    ) -> Dict:
        """5단계: 대표자 선정 및 저장

        Args:
            db: DB 세션
            df: 원본 데이터프레임
            X: 전처리된 피처 행렬
            labels: 클러스터 레이블
            user_ids: 유저 ID 배열

        Returns:
            representatives 딕셔너리
        """
        logger.info("대표자 선정 및 저장 시작")

        # 대표자 선정
        selector = RepresentativeSelector(n_representatives=3)
        representatives = selector.select_representatives(X, labels, user_ids)

        # 기존 대표자 삭제
        db.query(PersonaRepresentativeFeature).filter(
            PersonaRepresentativeFeature.as_of_date == self.as_of_date
        ).delete()

        logger.info(f"기존 대표자 데이터 삭제 완료")

        # 새 대표자 저장
        save_count = 0
        for persona_id, reps in representatives.items():
            # persona_id는 1부터 시작 (KMeans는 0-based이므로 +1)
            actual_persona_id = int(persona_id) + 1

            logger.info(
                f"대표자 저장: cluster_id={persona_id} -> persona_id={actual_persona_id}, "
                f"대표자 수={len(reps)}"
            )

            for user_id, rank, distance in reps:
                # user_id도 1부터 시작
                actual_user_id = int(user_id) + 1

                # 원본 유저 데이터 조회 (DataFrame의 user_id는 원본 그대로)
                user_row = df[df['user_id'] == user_id]

                if len(user_row) == 0:
                    logger.warning(f"user_id={user_id}에 해당하는 데이터를 찾을 수 없습니다.")
                    continue

                user_row = user_row.iloc[0]

                rep = PersonaRepresentativeFeature(
                    persona_id=actual_persona_id,
                    sample_rank=rank,
                    sample_label=f"REP_{actual_persona_id}_{rank}",
                    as_of_date=self.as_of_date,
                    age_band=user_row['age_band'],
                    primary_category=user_row['primary_category'],
                    core_keyword=user_row['core_keyword'],
                    trend_keyword=user_row['trend_keyword'],
                    price_sensitivity=user_row['price_sensitivity'],
                    benefit_sensitivity=user_row['benefit_sensitivity'],
                    brand_loyalty=user_row['brand_loyalty'],
                    purchase_style=user_row['purchase_style'],
                    price_sensitivity_score=user_row['price_sensitivity_score'],
                    benefit_sensitivity_score=user_row['benefit_sensitivity_score'],
                    brand_loyalty_score=user_row['brand_loyalty_score'],
                )
                db.add(rep)
                save_count += 1

        logger.info(f"{save_count}개 대표자 저장 완료")

        # DB에 flush하여 다음 단계에서 조회 가능하게 함 (autoflush=False이므로)
        db.flush()
        logger.info("대표자 데이터 flush 완료")

        return representatives

    def _update_persona_member_counts(self, db: Session, labels: np.ndarray):
        """6단계: persona.member_count 업데이트

        Args:
            db: DB 세션
            labels: 클러스터 레이블
        """
        logger.info("persona.member_count 업데이트 시작")

        unique, counts = np.unique(labels, return_counts=True)

        for persona_id, count in zip(unique, counts):
            # persona_id는 1부터 시작
            actual_persona_id = int(persona_id) + 1

            persona = db.query(Persona).filter(Persona.id == actual_persona_id).first()

            if persona:
                persona.member_count = int(count)
                persona.updated_at = datetime.utcnow()
                logger.info(f"Persona {actual_persona_id}: {int(count)}명")
            else:
                logger.warning(f"Persona {actual_persona_id} not found (이미 생성되어야 함)")

        logger.info(f"{len(unique)}개 페르소나 member_count 업데이트 완료")

    def _generate_persona_profiles(self, db: Session) -> Dict[int, Dict[str, str]]:
        """7단계: LLM을 사용한 페르소나 프로필 생성

        각 페르소나당 대표자 3명의 데이터를 조회하여 GPT-4o로 프로필을 생성합니다.

        Args:
            db: DB 세션

        Returns:
            {persona_id: {"name": "...", "profile_text": "..."}}

        Raises:
            개별 페르소나 실패 시 로그만 남기고 계속 진행
        """
        logger.info("=" * 60)
        logger.info("7단계: LLM 페르소나 프로필 생성 시작")
        logger.info("=" * 60)

        # DB flush 확인 (5단계에서 저장한 대표자가 조회 가능하도록)
        db.flush()
        logger.info("DB flush 완료 - 대표자 조회 준비")

        settings = get_settings()

        # LLM 클라이언트 초기화
        try:
            llm_client = LLMClient(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                temperature=settings.openai_temperature,
                max_tokens=settings.openai_max_tokens,
                timeout=settings.openai_timeout
            )
        except Exception as e:
            logger.error(f"LLM 클라이언트 초기화 실패: {e}", exc_info=True)
            raise

        profiles = {}
        success_count = 0
        failure_count = 0

        # 각 페르소나별로 프로필 생성
        for persona_id in range(1, self.n_clusters + 1):
            try:
                # 대표자 3명 조회
                logger.info(
                    f"Persona {persona_id} 대표자 조회 중... "
                    f"(persona_id={persona_id}, as_of_date={self.as_of_date})"
                )

                representatives = db.query(PersonaRepresentativeFeature).filter(
                    PersonaRepresentativeFeature.persona_id == persona_id,
                    PersonaRepresentativeFeature.as_of_date == self.as_of_date
                ).order_by(PersonaRepresentativeFeature.sample_rank).all()

                logger.info(f"Persona {persona_id} 대표자 조회 결과: {len(representatives)}명")

                if len(representatives) == 0:
                    # 디버깅: as_of_date로 저장된 모든 대표자 조회
                    all_reps = db.query(PersonaRepresentativeFeature).filter(
                        PersonaRepresentativeFeature.as_of_date == self.as_of_date
                    ).all()

                    logger.warning(
                        f"Persona {persona_id}의 대표자가 없습니다. "
                        f"(as_of_date={self.as_of_date}에 저장된 전체 대표자: {len(all_reps)}명)"
                    )

                    if len(all_reps) > 0:
                        # 어떤 persona_id가 있는지 확인
                        existing_persona_ids = set([rep.persona_id for rep in all_reps])
                        logger.warning(f"존재하는 persona_id: {sorted(existing_persona_ids)}")

                    failure_count += 1
                    continue

                # 대표자 데이터를 딕셔너리 리스트로 변환
                reps_data = []
                for rep in representatives:
                    rep_dict = {
                        "rank": rep.sample_rank,
                        "age_band": rep.age_band,
                        "primary_category": rep.primary_category,
                        "core_keyword": rep.core_keyword,
                        "trend_keyword": rep.trend_keyword,
                        "price_sensitivity": rep.price_sensitivity.value if rep.price_sensitivity else None,
                        "benefit_sensitivity": rep.benefit_sensitivity.value if rep.benefit_sensitivity else None,
                        "brand_loyalty": rep.brand_loyalty.value if rep.brand_loyalty else None,
                        "purchase_style": rep.purchase_style.value if rep.purchase_style else None,
                        "price_sensitivity_score": rep.price_sensitivity_score or 0.0,
                        "benefit_sensitivity_score": rep.benefit_sensitivity_score or 0.0,
                        "brand_loyalty_score": rep.brand_loyalty_score or 0.0,
                    }
                    reps_data.append(rep_dict)

                logger.info(
                    f"Persona {persona_id} 프로필 생성 중... "
                    f"(대표자 {len(reps_data)}명)"
                )

                # LLM 프로필 생성
                profile = llm_client.generate_persona_profile(
                    representatives_data=reps_data,
                    persona_id=persona_id
                )

                profiles[persona_id] = profile
                success_count += 1

                logger.info(
                    f"✓ Persona {persona_id} 프로필 생성 완료: "
                    f"이름='{profile['name']}', "
                    f"길이={len(profile['profile_text'])}자"
                )

            except Exception as e:
                logger.error(
                    f"✗ Persona {persona_id} 프로필 생성 실패: {e}",
                    exc_info=True
                )
                failure_count += 1
                # 개별 실패는 전체 배치를 중단하지 않음
                continue

        logger.info("=" * 60)
        logger.info(
            f"프로필 생성 완료 - 성공: {success_count}/{self.n_clusters}, "
            f"실패: {failure_count}/{self.n_clusters}"
        )
        logger.info("=" * 60)

        return profiles

    def _update_persona_profiles(
        self,
        db: Session,
        profiles: Dict[int, Dict[str, str]]
    ):
        """7.5단계: 생성된 프로필을 persona 테이블에 업데이트

        Args:
            db: DB 세션
            profiles: {persona_id: {"name": "...", "profile_text": "..."}}
        """
        logger.info("persona 테이블 프로필 업데이트 시작")

        update_count = 0

        for persona_id, profile in profiles.items():
            persona = db.query(Persona).filter(Persona.id == persona_id).first()

            if persona:
                persona.name = profile["name"]
                persona.profile_text = profile["profile_text"]
                persona.updated_at = datetime.utcnow()
                update_count += 1

                logger.info(
                    f"Persona {persona_id} 업데이트: "
                    f"{profile['name']} ({len(profile['profile_text'])}자)"
                )
            else:
                logger.warning(f"Persona {persona_id} not found (존재해야 함)")

        logger.info(f"{update_count}개 페르소나 프로필 업데이트 완료")

    def _run_item_matching(self, db: Session) -> Dict[str, Any]:
        """8단계: 페르소나-아이템 매칭 (벡터 유사도 + 협업 필터링)

        Args:
            db: DB 세션

        Returns:
            매칭 결과 딕셔너리
        """
        logger.info("=" * 60)
        logger.info("8단계: 페르소나-아이템 매칭 시작")
        logger.info("=" * 60)

        settings = get_settings()

        # 8.1: 클라이언트 초기화
        logger.info("8.1: 클라이언트 초기화")

        embedding_client = EmbeddingClient(settings.embedding_model)
        chroma_client = ChromaClient(settings.chroma_persist_dir)

        persona_embedder = PersonaEmbedder(embedding_client)
        item_embedder = ItemEmbedder(embedding_client)
        cf_filter = CollaborativeFilter()

        # 8.2: 페르소나 임베딩 생성
        logger.info("8.2: 페르소나 임베딩 생성")

        persona_ids = list(range(1, self.n_clusters + 1))
        persona_embeddings = persona_embedder.generate_all_persona_embeddings(
            db, persona_ids, self.as_of_date
        )

        logger.info(f"페르소나 임베딩: {len(persona_embeddings)}개 생성")

        # 8.3: 아이템 임베딩 생성
        logger.info("8.3: 아이템 임베딩 생성")

        item_embeddings = item_embedder.generate_all_item_embeddings(
            db, batch_size=settings.matching_batch_size
        )

        logger.info(f"아이템 임베딩: {len(item_embeddings)}개 생성")

        if not item_embeddings:
            logger.warning("아이템 임베딩이 없음 - 매칭 스킵")
            return {'interactions_saved': 0}

        # 8.4: ChromaDB에 저장
        logger.info("8.4: ChromaDB에 임베딩 저장")

        # 페르소나 임베딩 저장
        if persona_embeddings:
            chroma_client.add_embeddings(
                collection_name="personas",
                ids=[str(pid) for pid in persona_embeddings.keys()],
                embeddings=[emb.tolist() for emb in persona_embeddings.values()],
                metadatas=[{"persona_id": pid} for pid in persona_embeddings.keys()]
            )

        # 아이템 임베딩 저장
        chroma_client.add_embeddings(
            collection_name="items",
            ids=[str(item_id) for item_id in item_embeddings.keys()],
            embeddings=[emb.tolist() for emb in item_embeddings.values()],
            metadatas=[{"item_id": item_id} for item_id in item_embeddings.keys()]
        )

        # 8.5: 페르소나별 매칭
        logger.info("8.5: 페르소나별 매칭 시작")

        total_interactions = 0

        for persona_id in persona_ids:
            if persona_id not in persona_embeddings:
                logger.warning(f"Persona {persona_id}: 임베딩 없음 - 스킵")
                continue

            try:
                # 8.5.1: 유사도 계산 (Top N)
                persona_embedding = persona_embeddings[persona_id]

                search_result = chroma_client.search(
                    collection_name="items",
                    query_embedding=persona_embedding.tolist(),
                    n_results=settings.matching_top_n
                )

                similar_items = self._parse_similarity_results(search_result)

                # 8.5.2: 협업 필터링 (Top N)
                cf_items = cf_filter.calculate_cf_scores(
                    db, persona_id, top_n=settings.matching_top_n
                )

                # 8.5.3: 점수 결합 및 순위 결정
                final_items = self._merge_and_rank(
                    similar_items,
                    cf_items,
                    similarity_weight=settings.matching_similarity_weight,
                    cf_weight=settings.matching_cf_weight,
                    top_n=settings.matching_top_n
                )

                # 8.5.3.5: 판매 선호도 재랭킹 (NEW)
                final_items = self._rerank_with_sales_preference(
                    db,
                    final_items,
                    alpha=settings.reranking_alpha
                )

                # 8.5.4: DB 저장
                saved_count = self._save_interactions(db, persona_id, final_items)
                total_interactions += saved_count

                logger.info(
                    f"Persona {persona_id}: {saved_count}개 매칭 저장 "
                    f"(유사도: {len(similar_items)}, CF: {len(cf_items)})"
                )

            except Exception as e:
                logger.error(
                    f"Persona {persona_id} 매칭 실패: {e}",
                    exc_info=True
                )
                # 개별 페르소나 매칭 실패해도 패스
                continue

        logger.info("=" * 60)
        logger.info(f"페르소나-아이템 매칭 완료: 총 {total_interactions}개 저장")
        logger.info("=" * 60)

        return {'interactions_saved': total_interactions}

    def _parse_similarity_results(
        self,
        search_result: Dict[str, Any]
    ) -> List[Tuple[int, float]]:
        """ChromaDB 검색 결과를 (item_id, similarity_score) 리스트로 변환

        ChromaDB는 거리(distance)를 반환하므로 유사도로 변환:
        - distance가 낮을수록 유사함
        - similarity = 1 - distance (L2 distance 가정)

        Args:
            search_result: ChromaDB 검색 결과

        Returns:
            [(item_id, similarity_score), ...] 리스트
        """
        if not search_result['ids'] or not search_result['ids'][0]:
            return []

        item_ids = search_result['ids'][0]
        distances = search_result['distances'][0]

        # Distance를 유사도로 변환 (0~1 범위)
        # ChromaDB는 L2 distance를 반환
        # similarity = 1 / (1 + distance)
        similarities = [1.0 / (1.0 + dist) for dist in distances]

        results = [
            (int(item_id), similarity)
            for item_id, similarity in zip(item_ids, similarities)
        ]

        return results

    def _merge_and_rank(
        self,
        similar_items: List[Tuple[int, float]],
        cf_items: List[Tuple[int, float]],
        similarity_weight: float,
        cf_weight: float,
        top_n: int
    ) -> List[Dict[str, Any]]:
        """유사도와 CF 점수를 결합하여 최종 순위 결정

        Args:
            similar_items: [(item_id, similarity_score), ...]
            cf_items: [(item_id, cf_score), ...]
            similarity_weight: 유사도 가중치
            cf_weight: CF 가중치
            top_n: 최종 선택할 아이템 수

        Returns:
            [
                {
                    "item_id": int,
                    "rank": int,
                    "similarity_score": float,
                    "cf_score": float,
                    "final_score": float
                },
                ...
            ]
        """
        # 딕셔너리로 변환
        similarity_dict = {item_id: score for item_id, score in similar_items}
        cf_dict = {item_id: score for item_id, score in cf_items}

        # 모든 아이템 ID 수집
        all_item_ids = set(similarity_dict.keys()) | set(cf_dict.keys())

        # 최종 점수 계산
        scored_items = []

        for item_id in all_item_ids:
            sim_score = similarity_dict.get(item_id, 0.0)
            cf_score = cf_dict.get(item_id, 0.0)

            # 가중 평균
            final_score = similarity_weight * sim_score + cf_weight * cf_score

            scored_items.append({
                "item_id": item_id,
                "similarity_score": sim_score,
                "cf_score": cf_score,
                "final_score": final_score
            })

        # 최종 점수로 정렬
        scored_items.sort(key=lambda x: x['final_score'], reverse=True)

        # Top N 선택 및 순위 부여
        top_items = scored_items[:top_n]

        for rank, item in enumerate(top_items, start=1):
            item['rank'] = rank

        return top_items

    def _rerank_with_sales_preference(
        self,
        db: Session,
        items: List[Dict[str, Any]],
        alpha: float
    ) -> List[Dict[str, Any]]:
        """판매 선호도를 반영한 재랭킹

        Args:
            db: DB 세션
            items: 매칭된 아이템 리스트 (final_score 포함)
            alpha: 재랭킹 가중치 (0~1)
                   new_final = α * 기존_final + (1-α) * sales_preference

        Returns:
            재랭킹된 아이템 리스트
        """
        if not items:
            return []

        # 아이템 ID 수집
        item_ids = [item['item_id'] for item in items]

        # ItemFeature에서 sales_preference_score 조회
        item_features = db.query(ItemFeature).filter(
            ItemFeature.item_id.in_(item_ids)
        ).all()

        # item_id -> sales_preference_score 매핑
        sales_scores = {
            item.item_id: item.sales_preference_score or 0.0
            for item in item_features
        }

        # 재랭킹: 새로운 final_score 계산
        for item in items:
            item_id = item['item_id']
            current_final = item['final_score']
            sales_score = sales_scores.get(item_id, 0.0)

            # new_final = α * 기존_final + (1-α) * sales_preference
            new_final = alpha * current_final + (1 - alpha) * sales_score

            item['original_final_score'] = current_final
            item['sales_preference_score'] = sales_score
            item['final_score'] = new_final

        # 새로운 final_score로 재정렬
        items.sort(key=lambda x: x['final_score'], reverse=True)

        # 순위 재부여
        for rank, item in enumerate(items, start=1):
            item['rank'] = rank

        logger.debug(
            f"재랭킹 완료: {len(items)}개 아이템 "
            f"(α={alpha:.2f}, sales 가중치={(1-alpha):.2f})"
        )

        return items

    def _save_interactions(
        self,
        db: Session,
        persona_id: int,
        items: List[Dict[str, Any]]
    ) -> int:
        """매칭 결과를 persona_item 테이블에 저장

        Args:
            db: DB 세션
            persona_id: 페르소나 ID
            items: 매칭된 아이템 리스트

        Returns:
            저장된 레코드 수
        """
        if not items:
            return 0

        # 기존 매칭 삭제 (동일 persona_id)
        db.query(PersonaItem).filter(
            PersonaItem.persona_id == persona_id
        ).delete()

        # 새 매칭 저장
        for item in items:
            persona_item = PersonaItem(
                persona_id=persona_id,
                item_id=item['item_id'],
                item_rank=item['rank'],
                similarity_score=item['similarity_score'],
                score=item['cf_score'],  # score 필드에 cf_score 저장
                final_score=item['final_score']
            )
            db.add(persona_item)

        db.flush()

        return len(items)
