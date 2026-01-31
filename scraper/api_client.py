"""Cliente para API do ZapImóveis."""

import asyncio
import logging
import random
from typing import Optional

import httpx

from config import ScraperConfig
from .retry import retry_with_backoff_async

logger = logging.getLogger("zapimoveis_scraper.api_client")


class ZapImoveisClient:
    """Cliente para requisições à API do ZapImóveis."""

    def __init__(self, headers: Optional[dict] = None):
        self._headers = headers or ScraperConfig.get_headers()
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        """Inicia o cliente HTTP."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        logger.debug("Cliente HTTP iniciado")

    async def close(self) -> None:
        """Fecha o cliente HTTP."""
        if self._client:
            await self._client.aclose()
            logger.debug("Cliente HTTP fechado")

    def set_headers(self, headers: dict) -> None:
        """Define headers para requisições."""
        self._headers = headers

    @retry_with_backoff_async()
    async def _make_request(self, page: int) -> httpx.Response:
        """Faz requisição à API com retry."""
        params = ScraperConfig.get_api_params(page)

        logger.debug(f"Requisitando página {page} com params: {params}")

        response = await self._client.get(
            ScraperConfig.API_URL,
            params=params,
            headers=self._headers,
        )

        logger.debug(f"Resposta: status={response.status_code}")

        response.raise_for_status()
        return response

    async def fetch_listings(self, page: int = 1) -> dict:
        """Busca listagens de uma página específica."""
        logger.info(f"Buscando listagens - página {page}")

        response = await self._make_request(page)
        data = response.json()

        # Log de debug
        search_info = data.get("search", {})
        total = search_info.get("totalCount", 0)
        logger.info(f"Página {page}: Total de {total} imóveis disponíveis")

        return data

    async def fetch_all_listings(self, max_items: int = ScraperConfig.MAX_ITEMS) -> list:
        """Busca todas as listagens até o limite especificado."""
        all_listings = []
        page = 1
        total_count = None

        while True:
            # Delay entre requisições
            if page > 1:
                delay = random.uniform(
                    ScraperConfig.REQUEST_DELAY_MIN,
                    ScraperConfig.REQUEST_DELAY_MAX,
                )
                logger.debug(f"Aguardando {delay:.2f}s antes da próxima requisição...")
                await asyncio.sleep(delay)

            try:
                data = await self.fetch_listings(page)

                # Extrai listagens
                search_results = data.get("search", {})
                result_info = search_results.get("result", {})
                listings = result_info.get("listings", [])

                if total_count is None:
                    total_count = search_results.get("totalCount", 0)
                    logger.info(f"Total de imóveis disponíveis: {total_count}")

                if not listings:
                    logger.info("Nenhuma listagem encontrada nesta página")
                    break

                # Extrai dados de cada listing
                for item in listings:
                    listing = item.get("listing", {})
                    if listing:
                        all_listings.append(listing)

                logger.info(
                    f"Página {page}: {len(listings)} listagens extraídas. "
                    f"Total acumulado: {len(all_listings)}"
                )

                # Verifica se atingiu limite
                if len(all_listings) >= max_items:
                    logger.info(f"Limite de {max_items} itens atingido")
                    all_listings = all_listings[:max_items]
                    break

                # Verifica se há mais páginas
                if len(all_listings) >= total_count:
                    logger.info("Todas as listagens foram extraídas")
                    break

                page += 1

                # Limite de páginas como safety
                if page > ScraperConfig.MAX_PAGES:
                    logger.warning(f"Limite de {ScraperConfig.MAX_PAGES} páginas atingido")
                    break

            except Exception as e:
                logger.error(f"Erro ao buscar página {page}: {e}")
                break

        logger.info(f"Extração finalizada. Total: {len(all_listings)} listagens")
        return all_listings

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
