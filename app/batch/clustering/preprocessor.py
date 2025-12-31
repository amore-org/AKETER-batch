import logging
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from typing import Dict, List, Tuple


logger = logging.getLogger(__name__)


class FeaturePreprocessor:
    """유저 피처 전처리

    TopN+OTHER 전략을 사용하여 범주형 피처를 압축하고,
    One-Hot 인코딩 및 StandardScaler를 적용합니다.
    """

    def __init__(self, top_n: int = 10):
        """
        Args:
            top_n: 범주형 피처에서 유지할 상위 카테고리 수
        """
        self.top_n = top_n
        self.category_mappings: Dict[str, Dict[str, str]] = {}
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []

        # 피처 컬럼 정의
        self.numerical_columns = [
            'price_sensitivity_score',
            'benefit_sensitivity_score',
            'brand_loyalty_score'
        ]

        self.categorical_columns = [
            'age_band',
            'primary_category',
            'core_keyword',
            'trend_keyword'
        ]

        self.enum_columns = [
            'price_sensitivity',
            'benefit_sensitivity',
            'brand_loyalty',
            'purchase_style'
        ]

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """전처리 파이프라인 학습 및 변환

        Args:
            df: 원본 유저 피처 데이터프레임

        Returns:
            전처리된 피처 행렬 (numpy array)
        """
        logger.info("데이터 전처리 시작")

        # 복사본 생성
        df_processed = df.copy()

        # 1. 결측치 처리
        df_processed = self._handle_missing_values(df_processed)

        # 2. TopN+OTHER 변환 (범주형)
        df_processed = self._apply_topn_encoding(df_processed, fit=True)

        # 3. One-Hot Encoding (범주형)
        df_encoded = self._apply_onehot_encoding(df_processed, fit=True)

        # 4. Label Encoding (Enum)
        df_encoded = self._apply_label_encoding(df_encoded, fit=True)

        # 5. StandardScaler (모든 피처)
        X = self._apply_scaling(df_encoded, fit=True)

        logger.info(f"전처리 완료 - 피처 차원: {X.shape}")
        return X

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """학습된 전처리 파이프라인으로 변환

        Args:
            df: 원본 유저 피처 데이터프레임

        Returns:
            전처리된 피처 행렬 (numpy array)
        """
        df_processed = df.copy()
        df_processed = self._handle_missing_values(df_processed)
        df_processed = self._apply_topn_encoding(df_processed, fit=False)
        df_encoded = self._apply_onehot_encoding(df_processed, fit=False)
        df_encoded = self._apply_label_encoding(df_encoded, fit=False)
        X = self._apply_scaling(df_encoded, fit=False)
        return X

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """결측치 처리

        - 범주형: 'UNKNOWN'으로 채움
        - 수치형: 중앙값으로 채움
        """
        df = df.copy()

        # 범주형 및 Enum: UNKNOWN
        for col in self.categorical_columns + self.enum_columns:
            if col in df.columns:
                df[col] = df[col].fillna('UNKNOWN')

        # 수치형: 중앙값
        for col in self.numerical_columns:
            if col in df.columns:
                median_value = df[col].median()
                df[col] = df[col].fillna(median_value)

        return df

    def _apply_topn_encoding(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """TopN+OTHER 인코딩 적용

        Args:
            df: 데이터프레임
            fit: True면 카테고리 매핑 학습, False면 기존 매핑 사용

        Returns:
            변환된 데이터프레임
        """
        df = df.copy()

        for col in self.categorical_columns:
            if col not in df.columns:
                continue

            if fit:
                # 빈도수 계산
                value_counts = df[col].value_counts()

                # 상위 N개 카테고리
                top_categories = set(value_counts.head(self.top_n).index)

                # UNKNOWN은 항상 유지
                if 'UNKNOWN' in df[col].unique():
                    top_categories.add('UNKNOWN')

                # 매핑 저장
                self.category_mappings[col] = {
                    val: val if val in top_categories else 'OTHER'
                    for val in df[col].unique()
                }

                logger.info(f"TopN 인코딩 - {col}: {len(top_categories)}개 카테고리 유지")

            # 매핑 적용
            if col in self.category_mappings:
                df[col] = df[col].map(lambda x: self.category_mappings[col].get(x, 'OTHER'))

        return df

    def _apply_onehot_encoding(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """One-Hot Encoding 적용 (범주형 피처)

        Args:
            df: 데이터프레임
            fit: True면 인코더 학습

        Returns:
            인코딩된 데이터프레임
        """
        df = df.copy()

        # One-Hot Encoding
        df_encoded = pd.get_dummies(
            df,
            columns=self.categorical_columns,
            prefix=self.categorical_columns,
            drop_first=False
        )

        return df_encoded

    def _apply_label_encoding(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Label Encoding 적용 (Enum 피처)

        Args:
            df: 데이터프레임
            fit: True면 인코더 학습

        Returns:
            인코딩된 데이터프레임
        """
        df = df.copy()

        for col in self.enum_columns:
            if col not in df.columns:
                continue

            if fit:
                encoder = LabelEncoder()
                df[col] = encoder.fit_transform(df[col].astype(str))
                self.label_encoders[col] = encoder
            else:
                if col in self.label_encoders:
                    encoder = self.label_encoders[col]
                    # 학습 시 없던 값은 가장 빈번한 값으로 대체
                    df[col] = df[col].apply(
                        lambda x: x if x in encoder.classes_ else encoder.classes_[0]
                    )
                    df[col] = encoder.transform(df[col].astype(str))

        return df

    def _apply_scaling(self, df: pd.DataFrame, fit: bool = True) -> np.ndarray:
        """StandardScaler 적용

        Args:
            df: 데이터프레임
            fit: True면 스케일러 학습

        Returns:
            스케일링된 numpy array
        """
        # 피처 컬럼만 선택 (id, user_id 등 제외)
        feature_columns = [
            col for col in df.columns
            if col not in ['id', 'user_id', 'persona_id', 'as_of_date', 'created_at', 'updated_at']
        ]

        X = df[feature_columns].values

        if fit:
            X_scaled = self.scaler.fit_transform(X)
            self.feature_names = feature_columns
        else:
            X_scaled = self.scaler.transform(X)

        return X_scaled
