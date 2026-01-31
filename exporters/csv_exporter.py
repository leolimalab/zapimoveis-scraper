"""Exportador para formato CSV."""

import csv
import logging
from pathlib import Path
from typing import List

from models.property import Property
from config import ScraperConfig

logger = logging.getLogger("zapimoveis_scraper.csv_exporter")


class CSVExporter:
    """Exporta dados para CSV."""

    # Campos na ordem desejada (match Property.to_csv_row())
    FIELDNAMES = [
        "id",
        "tipo_imovel",
        "endereco_completo",
        "rua",
        "numero",
        "bairro",
        "cidade",
        "estado",
        "tamanho_m2",
        "quartos",
        "banheiros",
        "vagas",
        "preco",
        "condominio",
        "iptu",
        "titulo",
        "descricao",
        "caracteristicas_imovel",
        "caracteristicas_condominio",
        "pets_permitidos",
        "anunciante",
        "anunciante_tipo",
        "anunciante_contato",
        "data_publicacao",
        "data_atualizacao",
        "data_extracao",
        "avaliacao",
        "url",
    ]

    def __init__(self, output_dir: Path = ScraperConfig.OUTPUT_DIR):
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        properties: List[Property],
        filename: str = ScraperConfig.CSV_FILENAME,
    ) -> Path:
        """Exporta lista de propriedades para CSV."""
        output_path = self._output_dir / filename

        logger.info(f"Exportando {len(properties)} imóveis para {output_path}")

        try:
            # UTF-8 com BOM para Excel reconhecer acentos
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=self.FIELDNAMES,
                    delimiter=";",  # Padrão brasileiro
                    quoting=csv.QUOTE_MINIMAL,
                )

                writer.writeheader()

                for prop in properties:
                    writer.writerow(prop.to_csv_row())

            logger.info(f"CSV exportado com sucesso: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Erro ao exportar CSV: {e}")
            raise
