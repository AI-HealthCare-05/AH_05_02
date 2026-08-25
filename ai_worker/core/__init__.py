import logging

from ai_worker.core.config import Config
from ai_worker.core.logger import setup_logger


def get_config() -> Config:
    return Config()


config = get_config()
logger: logging.Logger = setup_logger()
