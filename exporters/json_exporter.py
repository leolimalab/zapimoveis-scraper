"""Exportador para formato JSON."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from models.property import Property
from config import ScraperConfig

logger = logging.getLogger("zapimoveis_scraper.json_exporter")


class JSONExporter:
    """Exporta dados para JSON."""

    def __init__(self, output_dir: Path = ScraperConfig.OUTPUT_DIR):
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        properties: List[Property],
        filename: str = ScraperConfig.JSON_FILENAME,
    ) -> Path:
        """Exporta lista de propriedades para JSON."""
        output_path = self._output_dir / filename

        logger.info(f"Exportando {len(properties)} imóveis para {output_path}")

        try:
            # Prepara dados com metadados
            data = {
                "metadata": {
                    "fonte": "ZapImóveis",
                    "url_base": ScraperConfig.BASE_URL,
                    "bairro": ScraperConfig.NEIGHBORHOOD,
                    "cidade": ScraperConfig.CITY,
                    "data_extracao": datetime.now().isoformat(),
                    "total_imoveis": len(properties),
                },
                "imoveis": [prop.to_dict() for prop in properties],
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"JSON exportado com sucesso: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Erro ao exportar JSON: {e}")
            raise
