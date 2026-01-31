#!/usr/bin/env python3
"""
Web Scraper ZapImóveis - Imóveis Leme/RJ

Extrai dados de apartamentos à venda no Leme (RJ) do ZapImóveis,
salvando em CSV e JSON com retry exponencial e logging detalhado.
"""

import asyncio
import sys
from datetime import datetime

from config import ScraperConfig
from utils.logger import setup_logger, get_logger
from scraper.html_extractor import HTMLExtractor
from exporters.csv_exporter import CSVExporter
from exporters.json_exporter import JSONExporter


async def main() -> int:
    """Função principal do scraper."""
    # Inicializa logging
    setup_logger()
    logger = get_logger()

    logger.info("=" * 60)
    logger.info("ZapImóveis Scraper - Iniciando")
    logger.info(f"Bairro: {ScraperConfig.NEIGHBORHOOD}")
    logger.info(f"Cidade: {ScraperConfig.CITY}")
    logger.info(f"Limite de imóveis: {ScraperConfig.MAX_ITEMS}")
    logger.info("=" * 60)

    start_time = datetime.now()

    try:
        # 1. Extrai imóveis via Playwright (HTML/DOM)
        logger.info("Fase 1: Extraindo imóveis via Playwright...")

        async with HTMLExtractor() as extractor:
            properties = await extractor.extract_all(
                max_items=ScraperConfig.MAX_ITEMS
            )

        if not properties:
            logger.warning("Nenhum imóvel encontrado!")
            return 1

        logger.info(f"Total de imóveis extraídos: {len(properties)}")

        # 2. Exporta para CSV
        logger.info("Fase 2: Exportando para CSV...")

        csv_exporter = CSVExporter()
        csv_path = csv_exporter.export(properties)

        # 3. Exporta para JSON
        logger.info("Fase 3: Exportando para JSON...")

        json_exporter = JSONExporter()
        json_path = json_exporter.export(properties)

        # 4. Relatório final
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("=" * 60)
        logger.info("RELATÓRIO FINAL")
        logger.info("=" * 60)
        logger.info(f"Imóveis extraídos: {len(properties)}")
        logger.info(f"Tempo total: {duration:.2f}s")
        logger.info(f"Arquivo CSV: {csv_path}")
        logger.info(f"Arquivo JSON: {json_path}")
        logger.info("=" * 60)

        # Estatísticas dos imóveis
        if properties:
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
        logger.info("Scraping concluído com sucesso!")

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
