"""OpenAI API 호출 클라이언트"""

from typing import Optional, Dict, Any, List
import logging
from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 60
    ):
        """LLM 클라이언트 초기화

        Args:
            api_key: OpenAI API 키
            model: 사용할 모델명 (예: gpt-4o, gpt-4o-mini)
            temperature: 생성 다양성 (0.0-2.0)
            max_tokens: 최대 생성 토큰 수
            timeout: API 타임아웃 (초)
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        # OpenAI 클라이언트 초기화
        self.client = OpenAI(
            api_key=api_key,
            timeout=timeout
        )

        logger.info(f"LLM 클라이언트 초기화: model={model}, temp={temperature}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, ConnectionError)),
        before_sleep=lambda retry_state: logger.warning(
            f"API 호출 재시도 {retry_state.attempt_number}/3 "
            f"(이유: {retry_state.outcome.exception()})"
        )
    )
    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """OpenAI Chat Completion API 호출

        Args:
            messages: 메시지 리스트
                [
                    {"role": "system", "content": "..."},
                    {"role": "user", "content": "..."}
                ]
            temperature: 오버라이드 temperature (선택)
            max_tokens: 오버라이드 max_tokens (선택)

        Returns:
            생성된 텍스트

        Raises:
            APIError: API 호출 실패 (3회 재시도 후)
            ValueError: 잘못된 파라미터
        """
        try:
            logger.debug(f"API 호출 시작: model={self.model}")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens
            )

            content = response.choices[0].message.content

            logger.debug(
                f"API 호출 성공: "
                f"tokens={response.usage.total_tokens}, "
                f"output_length={len(content)}"
            )

            return content

        except (RateLimitError, APITimeoutError, ConnectionError) as e:
            # 재시도 대상 예외 - tenacity가 처리
            logger.warning(f"재시도 가능한 에러 발생: {type(e).__name__}")
            raise

        except APIError as e:
            logger.error(f"OpenAI API 에러: {e}", exc_info=True)
            raise

        except Exception as e:
            logger.error(f"예상치 못한 에러: {e}", exc_info=True)
            raise

    def generate_persona_profile(
        self,
        representatives_data: List[Dict[str, Any]],
        persona_id: int
    ) -> Dict[str, str]:
        """페르소나 프로필 생성 (이름 + 설명)

        Args:
            representatives_data: 대표자 3명의 피처 데이터
            persona_id: 페르소나 ID

        Returns:
            {"name": "페르소나 이름", "profile_text": "프로필 설명"}
        """
        logger.info(f"Persona {persona_id} 프로필 생성 요청 (대표자 {len(representatives_data)}명)")

        # 대표자 데이터 포맷팅
        reps_text = self._format_representatives(representatives_data)

        # 프롬프트 구성
        system_message = """당신은 화장품 이커머스 플랫폼의 고객 페르소나 분석 전문가입니다.
고객 행동 데이터를 기반으로 페르소나의 특성을 한국어로 명확하게 설명하는 역할을 합니다.

다음 지침을 따르세요:
1. 페르소나 이름은 직관적이고 기억하기 쉬운 이름으로 작성
2. 프로필은 자연스러운 한국어 문장으로 작성 (JSON이나 마크다운 형식 사용 금지)
3. 대표자 3명의 공통된 행동 패턴과 특징을 중심으로 설명
4. 구매 스타일, 선호 카테고리, 가격 민감도, 브랜드 충성도를 자연스럽게 녹여냄
5. 페르소나에 알맞는 마케팅 톤앤매너를 가이드
6. 프로필은 85자로 간결하게 작성. 85자를 넘으면 안 됨."""

        user_message = f"""다음은 Persona {persona_id}의 대표 고객 3명의 행동 데이터입니다:

{reps_text}

이 데이터를 바탕으로:
1. 이 페르소나를 대표하는 **한국어 이름** (5-15자)
2. 이 페르소나의 특징을 설명해주고 톤앤매너를 가이드해주는 **자연스러운 한국어 프로필** (85자)

를 생성해주세요.

출력 형식:
이름: [페르소나 이름]
프로필: [자연스러운 한국어 문장으로 된 프로필]"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]

        # API 호출
        response_text = self.generate_completion(messages)

        # 응답 파싱
        profile = self._parse_profile_response(response_text, persona_id)

        logger.info(
            f"Persona {persona_id} 프로필 생성 완료: "
            f"이름='{profile['name']}', 길이={len(profile['profile_text'])}자"
        )

        return profile

    def _format_representatives(self, reps_data: List[Dict[str, Any]]) -> str:
        """대표자 데이터를 읽기 쉬운 텍스트로 포맷팅

        Args:
            reps_data: 대표자 데이터 리스트

        Returns:
            포맷팅된 텍스트
        """
        lines = []

        for i, rep in enumerate(reps_data, 1):
            lines.append(f"[대표 고객 {i}]")
            lines.append(f"- 연령대: {rep.get('age_band') or '미상'}")
            lines.append(f"- 주요 관심 카테고리: {rep.get('primary_category') or '미상'}")
            lines.append(f"- 핵심 키워드: {rep.get('core_keyword') or '미상'}")
            lines.append(f"- 트렌드 키워드: {rep.get('trend_keyword') or '미상'}")

            price_score = rep.get('price_sensitivity_score', 0.0)
            lines.append(f"- 가격 민감도: {rep.get('price_sensitivity') or '미상'} (점수: {price_score:.2f})")

            benefit_score = rep.get('benefit_sensitivity_score', 0.0)
            lines.append(f"- 혜택 민감도: {rep.get('benefit_sensitivity') or '미상'} (점수: {benefit_score:.2f})")

            loyalty_score = rep.get('brand_loyalty_score', 0.0)
            lines.append(f"- 브랜드 충성도: {rep.get('brand_loyalty') or '미상'} (점수: {loyalty_score:.2f})")

            lines.append(f"- 구매 스타일: {rep.get('purchase_style') or '미상'}")
            lines.append("")  # 빈 줄

        return "\n".join(lines)

    def _parse_profile_response(self, response_text: str, persona_id: int) -> Dict[str, str]:
        """LLM 응답에서 이름과 프로필 추출

        예상 응답 형식:
            이름: 트렌드 헌터
            프로필: 최신 뷰티 트렌드를 빠르게 캐치하고...

        Args:
            response_text: LLM 응답 텍스트
            persona_id: 페르소나 ID (기본값 생성용)

        Returns:
            {"name": "...", "profile_text": "..."}
        """
        lines = response_text.strip().split('\n')
        name = None
        profile_text = None

        for line in lines:
            line = line.strip()
            if line.startswith("이름:"):
                name = line.replace("이름:", "").strip()
            elif line.startswith("프로필:"):
                profile_text = line.replace("프로필:", "").strip()

        # 파싱 실패 시 기본값
        if not name:
            logger.warning(f"Persona {persona_id}: 응답에서 이름을 찾을 수 없음. 기본값 사용")
            name = f"Persona {persona_id}"

        if not profile_text:
            logger.warning(f"Persona {persona_id}: 응답에서 프로필을 찾을 수 없음. 기본값 사용")
            profile_text = "상세 프로필 생성 중입니다."

        return {
            "name": name[:100],  # DB VARCHAR(100) 제한
            "profile_text": profile_text
        }
