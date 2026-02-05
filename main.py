#!/usr/bin/env python3
"""
Web Scraper ZapImóveis

Extrai dados de apartamentos à venda do ZapImóveis,
salvando em CSV e JSON com logging detalhado.

Uso:
    python main.py                              # Padrão: Leme/RJ
    python main.py --busca "Rua Gustavo Sampaio"
    python main.py --bairro Copacabana
    python main.py --limite 200
"""

import argparse
import asyncio
import sys
from datetime import datetime

from config import ScraperConfig
from utils.logger import setup_logger, get_logger
from scraper.html_extractor import HTMLExtractor
from exporters.csv_exporter import CSVExporter
from exporters.json_exporter import JSONExporter


def parse_args() -> argparse.Namespace:
    """Processa argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Scraper de imóveis do ZapImóveis"
    )
    parser.add_argument(
        "--busca",
        type=str,
        default="",
        help='Termo de busca (ex: "Rua Gustavo Sampaio", "Av. Atlântica")',
    )
    parser.add_argument(
        "--bairro",
        type=str,
        default=ScraperConfig.NEIGHBORHOOD,
        help=f"Bairro para busca (padrão: {ScraperConfig.NEIGHBORHOOD})",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=ScraperConfig.MAX_ITEMS,
        help=f"Número máximo de imóveis (padrão: {ScraperConfig.MAX_ITEMS})",
    )
    return parser.parse_args()


async def main() -> int:
    """Função principal do scraper."""
    args = parse_args()

    # Aplica configurações da CLI
    ScraperConfig.SEARCH_TERM = args.busca
    ScraperConfig.NEIGHBORHOOD = args.bairro
    ScraperConfig.MAX_ITEMS = args.limite
    ScraperConfig.MAX_PAGES = max(1, (args.limite + ScraperConfig.PAGE_SIZE - 1) // ScraperConfig.PAGE_SIZE)

    setup_logger()
    logger = get_logger()

    logger.info("=" * 60)
    logger.info("ZapImóveis Scraper - Iniciando")
    logger.info(f"Bairro: {ScraperConfig.NEIGHBORHOOD}")
    logger.info(f"Cidade: {ScraperConfig.CITY}")
    if ScraperConfig.SEARCH_TERM:
        logger.info(f"Busca: {ScraperConfig.SEARCH_TERM}")
    logger.info(f"Limite de imóveis: {ScraperConfig.MAX_ITEMS}")
    logger.info("=" * 60)

    start_time = datetime.now()

    try:
        logger.info("Extraindo imóveis via Playwright...")

        async with HTMLExtractor() as extractor:
            properties = await extractor.extract_all(
                max_items=ScraperConfig.MAX_ITEMS
            )

        if not properties:
            logger.warning("Nenhum imóvel encontrado!")
            return 1

        logger.info(f"Total de imóveis extraídos: {len(properties)}")

        csv_exporter = CSVExporter()
        csv_path = csv_exporter.export(properties)

        json_exporter = JSONExporter()
        json_path = json_exporter.export(properties)

        duration = (datetime.now() - start_time).total_seconds()

        logger.info("=" * 60)
        logger.info("RELATÓRIO FINAL")
        logger.info("=" * 60)
        logger.info(f"Imóveis extraídos: {len(properties)}")
        logger.info(f"Tempo total: {duration:.2f}s")
        logger.info(f"Arquivo CSV: {csv_path}")
        logger.info(f"Arquivo JSON: {json_path}")

        precos = [p.preco for p in properties if p.preco > 0]
        areas = [p.tamanho_m2 for p in properties if p.tamanho_m2 > 0]

        if precos:
            logger.info(f"Preço mínimo: R$ {min(precos):,.2f}")
            logger.info(f"Preço máximo: R$ {max(precos):,.2f}")
            logger.info(f"Preço médio: R$ {sum(precos)/len(precos):,.2f}")

        if areas:
            logger.info(f"Área mínima: {min(areas)} m²")
            logger.info(f"Área máxima: {max(areas)} m²")
            logger.info(f"Área média: {sum(areas)/len(areas):.1f} m²")

        logger.info("=" * 60)
        return 0

    except KeyboardInterrupt:
        logger.warning("Execução interrompida pelo usuário")
        return 130

    except Exception as e:
        logger.critical(f"Erro fatal: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
