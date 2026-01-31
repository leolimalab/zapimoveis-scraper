"""Gestão do Playwright para estabelecer sessão."""

import asyncio
import logging
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Request

from config import ScraperConfig

logger = logging.getLogger("zapimoveis_scraper.browser")


class BrowserManager:
    """Gerencia instância do browser Playwright."""

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._cookies: list = []
        self._headers: dict = {}
        self._api_headers: dict = {}

    async def start(self) -> None:
        """Inicia o browser e estabelece sessão."""
        logger.info("Iniciando Playwright browser...")

        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            headless=ScraperConfig.HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        self._context = await self._browser.new_context(
            user_agent=ScraperConfig.USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="pt-BR",
        )

        self._page = await self._context.new_page()

        # Intercepta requisições para capturar headers da API
        self._page.on("request", self._capture_api_headers)

        # Navega para estabelecer sessão
        await self._establish_session()

    def _capture_api_headers(self, request: Request) -> None:
        """Captura headers de requisições à API."""
        if "glue-api.zapimoveis.com.br" in request.url:
            headers = request.headers
            if headers:
                self._api_headers = dict(headers)
                logger.debug(f"Headers da API capturados: {list(headers.keys())}")

    async def _establish_session(self) -> None:
        """Navega para o site para estabelecer sessão válida."""
        search_url = (
            f"{ScraperConfig.BASE_URL}/venda/apartamentos/"
            f"rj+rio-de-janeiro+zona-sul+leme/"
        )

        logger.info(f"Navegando para {search_url} para estabelecer sessão...")

        try:
            await self._page.goto(search_url, wait_until="networkidle", timeout=60000)

            # Aguarda carregamento completo e possível Cloudflare challenge
            await asyncio.sleep(5)

            # Scroll para carregar mais conteúdo e disparar requisições API
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(2)

            # Captura cookies
            self._cookies = await self._context.cookies()
            logger.debug(f"Cookies capturados: {len(self._cookies)}")

            # Monta headers com cookies
            cookie_string = "; ".join(
                f"{c['name']}={c['value']}" for c in self._cookies
            )

            # Usa headers capturados da API ou headers padrão
            if self._api_headers:
                self._headers = self._api_headers.copy()
                logger.info("Usando headers capturados da API real")
            else:
                self._headers = ScraperConfig.get_headers()
                logger.info("Usando headers padrão (API não interceptada)")

            if cookie_string:
                self._headers["Cookie"] = cookie_string

            logger.info("Sessão estabelecida com sucesso")

        except Exception as e:
            logger.error(f"Erro ao estabelecer sessão: {e}")
            raise

    def get_cookies(self) -> list:
        """Retorna cookies da sessão."""
        return self._cookies

    def get_headers(self) -> dict:
        """Retorna headers com cookies da sessão."""
        return self._headers

    async def close(self) -> None:
        """Fecha o browser."""
        logger.info("Fechando browser...")

        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        logger.info("Browser fechado")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
