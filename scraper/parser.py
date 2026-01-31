"""Parser para dados de listagens."""

import logging
from typing import List, Optional

from models.property import Property

logger = logging.getLogger("zapimoveis_scraper.parser")


class ListingParser:
    """Parser para converter dados da API em objetos Property."""

    def __init__(self):
        self._parsed_count = 0
        self._error_count = 0
        self._skipped_ids = set()

    def parse_listing(self, listing: dict) -> Optional[Property]:
        """Converte dados de uma listagem em Property."""
        listing_id = listing.get("id", "unknown")

        try:
            property_obj = Property.from_api_data(listing)

            if property_obj:
                self._parsed_count += 1
                logger.debug(
                    f"Parsed: {property_obj.id} - {property_obj.descricao[:50]}..."
                )
                return property_obj
            else:
                self._error_count += 1
                self._skipped_ids.add(listing_id)
                logger.warning(f"Falha ao parsear listagem {listing_id}")
                return None

        except Exception as e:
            self._error_count += 1
            self._skipped_ids.add(listing_id)
            logger.error(f"Erro ao parsear listagem {listing_id}: {e}")
            return None

    def parse_listings(self, listings: List[dict]) -> List[Property]:
        """Converte lista de dados em lista de Properties."""
        logger.info(f"Iniciando parse de {len(listings)} listagens...")

        properties = []

        for listing in listings:
            property_obj = self.parse_listing(listing)
            if property_obj:
                properties.append(property_obj)

        logger.info(
            f"Parse concluído: {self._parsed_count} sucesso, "
            f"{self._error_count} erros"
        )

        return properties

    def get_stats(self) -> dict:
        """Retorna estatísticas do parsing."""
        return {
            "parsed": self._parsed_count,
            "errors": self._error_count,
            "skipped_ids": list(self._skipped_ids),
        }

    def reset_stats(self) -> None:
        """Reseta estatísticas."""
        self._parsed_count = 0
        self._error_count = 0
        self._skipped_ids = set()
