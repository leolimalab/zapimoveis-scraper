"""Configuração de logging detalhado."""

import logging
import logging.handlers
from pathlib import Path

from config import ScraperConfig


def setup_logger() -> logging.Logger:
    """Configura e retorna o logger principal."""
    # Cria diretório de output se não existir
    ScraperConfig.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log_file = ScraperConfig.OUTPUT_DIR / ScraperConfig.LOG_FILENAME

    # Formato detalhado
    detailed_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_format)

    # Handler para arquivo com rotação
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_format)

    # Logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Logger específico do scraper
    logger = logging.getLogger("zapimoveis_scraper")
    logger.setLevel(logging.DEBUG)

    return logger


def get_logger(name: str = "zapimoveis_scraper") -> logging.Logger:
    """Obtém logger com nome específico."""
    return logging.getLogger(name)
