import logging
import sys
from pathlib import Path


def setup_logging(log_dir: str = "logs", log_level: str = "INFO") -> logging.Logger:
    """로깅 설정

    Args:
        log_dir: 로그 파일 저장 디렉토리
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        설정된 루트 로거
    """
    # 로그 디렉토리 생성
    Path(log_dir).mkdir(exist_ok=True)

    # 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 파일 핸들러
    file_handler = logging.FileHandler(
        f"{log_dir}/batch.log",
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, log_level))

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level))

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # 기존 핸들러 제거 (중복 방지)
    root_logger.handlers.clear()

    # 핸들러 추가
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger
