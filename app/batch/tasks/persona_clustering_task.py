from datetime import date, datetime, timedelta
import logging
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import SessionLocal
from app.models import UserFeature, Persona, PersonaRepresentativeFeature
from app.batch.clustering import FeaturePreprocessor, PersonaClusterer, RepresentativeSelector


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
                'cluster_distribution': cluster_distribution
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
        """1단계: user_feature 데이터 로드

        Args:
            db: DB 세션

        Returns:
            유저 피처 데이터프레임
        """
        logger.info(f"DB에서 user_feature 데이터 로드 중... (as_of_date={self.as_of_date})")

        query = db.query(UserFeature).filter(
            UserFeature.as_of_date == self.as_of_date
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
            # persona_id는 1부터 시작
            actual_persona_id = int(persona_id) + 1

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
