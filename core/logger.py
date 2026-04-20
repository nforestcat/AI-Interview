import logging
import os

def get_logger(name: str):
    """콘솔과 파일에 동시에 로그를 남기는 로거를 반환합니다."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 이미 핸들러가 설정되어 있다면 중복 방지
    if not logger.handlers:
        # 1. 파일 핸들러 (app_log.log)
        file_handler = logging.FileHandler("app_log.log", encoding="utf-8")
        file_formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # 2. 콘솔 핸들러 (터미널 출력)
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger
