"""Extrator de dados diretamente do HTML via Playwright."""

import asyncio
import glob
import json
import logging
import random
import re
import traceback
from pathlib import Path
from typing import List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from config import ScraperConfig
from models.property import Property

logger = logging.getLogger("zapimoveis_scraper.html_extractor")


class HTMLExtractor:
    """Extrai dados de imóveis diretamente do HTML renderizado."""

    def __init__(self, fetch_details: bool = True):
        """
        Inicializa o extrator.

        Args:
            fetch_details: Se True, busca dados adicionais das páginas de detalhe
        """
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._fetch_details = fetch_details

    async def start(self) -> None:
        """Inicia o browser."""
        logger.info("Iniciando Playwright browser...")

        self._playwright = await async_playwright().start()

        # Tenta usar o executável padrão; se não existir, busca no cache
        launch_kwargs = {
            "headless": ScraperConfig.HEADLESS,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        }

        # Detecta executável do Chromium disponível no cache do Playwright
        cache_dir = Path.home() / ".cache" / "ms-playwright"
        for pattern in ["chromium-*/chrome-linux/chrome", "chromium_headless_shell-*/chrome-linux/headless_shell"]:
            matches = sorted(glob.glob(str(cache_dir / pattern)), reverse=True)
            if matches:
                launch_kwargs["executable_path"] = matches[0]
                logger.info(f"Usando Chromium: {matches[0]}")
                break

        self._browser = await self._playwright.chromium.launch(**launch_kwargs)

        self._context = await self._browser.new_context(
            user_agent=ScraperConfig.USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="pt-BR",
        )

    async def close(self) -> None:
        """Fecha o browser."""
        logger.info("Fechando browser...")

        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        logger.info("Browser fechado")

    async def extract_all(self, max_items: int = ScraperConfig.MAX_ITEMS) -> List[Property]:
        """Extrai todos os imóveis até o limite especificado."""
        all_properties = []
        seen_ids = set()
        page_num = 1

        while len(all_properties) < max_items:
            url = ScraperConfig.get_search_url(page_num)

            logger.info(f"Extraindo página {page_num}: {url}")

            try:
                properties = await self._extract_listing_page(url)

                if not properties:
                    logger.info("Nenhum imóvel encontrado nesta página")
                    break

                # Filtra duplicados
                new_properties = []
                for prop in properties:
                    if prop.id not in seen_ids:
                        seen_ids.add(prop.id)
                        new_properties.append(prop)

                if not new_properties:
                    logger.info("Apenas duplicados encontrados, finalizando")
                    break

                all_properties.extend(new_properties)
                logger.info(
                    f"Página {page_num}: {len(new_properties)} novos imóveis. "
                    f"Total acumulado: {len(all_properties)}"
                )

                if len(all_properties) >= max_items:
                    all_properties = all_properties[:max_items]
                    break

                # Delay entre páginas
                delay = random.uniform(
                    ScraperConfig.REQUEST_DELAY_MIN,
                    ScraperConfig.REQUEST_DELAY_MAX,
                )
                await asyncio.sleep(delay)

                page_num += 1

                if page_num > ScraperConfig.MAX_PAGES:
                    logger.info(f"Limite de {ScraperConfig.MAX_PAGES} páginas atingido")
                    break

            except Exception as e:
                logger.error(f"Erro ao extrair página {page_num}: {e}")
                break

        # Busca dados adicionais das páginas de detalhe
        if self._fetch_details and all_properties:
            logger.info("Buscando dados adicionais das páginas de detalhe...")
            all_properties = await self._enrich_properties(all_properties)

        logger.info(f"Extração finalizada. Total: {len(all_properties)} imóveis")
        return all_properties

    async def _extract_listing_page(self, url: str) -> List[Property]:
        """Extrai imóveis de uma página de listagem."""
        properties = []

        try:
            page = await self._context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)

                # Aguarda seletor de listagem (mais rápido que sleep fixo)
                try:
                    await page.wait_for_selector(
                        'script[type="application/ld+json"]',
                        timeout=10000,
                    )
                except Exception:
                    pass  # Timeout — continua tentando extrair

                # Extrai dados do schema.org
                json_data = await self._extract_schema_org(page)

                if json_data and "itemList" in json_data:
                    items = json_data["itemList"].get("itemListElement", [])
                    logger.info(f"Encontrados {len(items)} itens no ItemList (schema.org)")

                    for item in items:
                        prop = Property.from_schema_org(item)
                        if prop:
                            properties.append(prop)

            finally:
                await page.close()

        except Exception as e:
            logger.error(f"Erro ao extrair página de listagem: {e}")

        return properties

    async def _extract_schema_org(self, page: Page) -> Optional[dict]:
        """Extrai dados do schema.org da página."""
        try:
            scripts = await page.evaluate("""
                () => {
                    const scripts = [];
                    document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
                        scripts.push(s.textContent);
                    });
                    return scripts;
                }
            """)

            for script in scripts:
                try:
                    data = json.loads(script)
                    if data.get("@type") == "ItemList":
                        return {"itemList": data}
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            logger.error(f"Erro ao extrair schema.org: {e}")

        return None

    async def _enrich_properties(self, properties: List[Property]) -> List[Property]:
        """Enriquece propriedades com dados das páginas de detalhe.

        Usa semáforo para limitar concorrência e evitar bloqueio anti-bot.
        """
        semaphore = asyncio.Semaphore(ScraperConfig.DETAIL_CONCURRENCY)
        total = len(properties)
        counter = {"done": 0}

        async def _enrich_one(prop: Property) -> Property:
            async with semaphore:
                counter["done"] += 1
                logger.info(f"Buscando detalhes {counter['done']}/{total}: {prop.id}")
                try:
                    result = await self._fetch_property_details(prop)
                except Exception as e:
                    logger.warning(f"Erro ao buscar detalhes de {prop.id}: {e}")
                    result = prop

                # Delay para rate limiting
                delay = random.uniform(
                    ScraperConfig.REQUEST_DELAY_MIN,
                    ScraperConfig.REQUEST_DELAY_MAX,
                )
                await asyncio.sleep(delay)
                return result

        return await asyncio.gather(*[_enrich_one(p) for p in properties])

    async def _fetch_property_details(self, prop: Property) -> Property:
        """Busca dados adicionais da página de detalhe do imóvel."""
        page = await self._context.new_page()

        try:
            await page.goto(prop.url, wait_until="networkidle", timeout=60000)

            # Aguarda indicador de conteúdo carregado
            try:
                await page.wait_for_selector(
                    '[data-testid*="price"], [class*="price"], [class*="Price"]',
                    timeout=8000,
                )
            except Exception:
                pass  # Timeout — verifica via Cloudflare check abaixo

            # Verifica se página foi bloqueada por Cloudflare
            if await self._is_cloudflare_blocked(page):
                logger.warning(f"Página bloqueada pelo Cloudflare para {prop.id}")
                return prop

            # Extrai dados adicionais do DOM
            details = await self._extract_detail_data(page)
            logger.debug(f"Details extraídos para {prop.id}: {details}")

            # Atualiza propriedade com dados adicionais
            if details.get("iptu"):
                prop.iptu = details["iptu"]

            if details.get("endereco_completo"):
                prop.endereco_completo = details["endereco_completo"]
                match = re.search(r',?\s*(\d+)', details["endereco_completo"])
                if match:
                    prop.numero = match.group(1)

            if details.get("anunciante"):
                prop.anunciante = details["anunciante"]

            if details.get("anunciante_tipo"):
                prop.anunciante_tipo = details["anunciante_tipo"]

            if details.get("caracteristicas_condominio"):
                prop.caracteristicas_condominio = details["caracteristicas_condominio"]

            if details.get("data_atualizacao"):
                prop.data_atualizacao = details["data_atualizacao"]

            if details.get("data_publicacao"):
                prop.data_publicacao = details["data_publicacao"]

        except Exception as e:
            logger.debug(f"Erro ao buscar detalhes de {prop.id}: {e}")

        finally:
            await page.close()

        return prop

    async def _extract_detail_data(self, page: Page) -> dict:
        """Extrai dados da página de detalhe."""
        details = {}

        try:
            # Extrai todo o texto da página para análise
            page_text = await page.evaluate("() => document.body.innerText")
            logger.debug(f"Page text length: {len(page_text)}")

            # IPTU - busca valor numérico após "IPTU"
            iptu_match = re.search(r'IPTU[:\s]*R?\$?\s*([\d.,]+)', page_text, re.IGNORECASE)
            if iptu_match:
                details["iptu"] = Property.parse_price(iptu_match.group(1))

            # Endereço completo
            endereco_elem = await page.query_selector('[data-testid="address-text"], [class*="address"], [class*="location"] h1, [class*="Address"]')
            if endereco_elem:
                details["endereco_completo"] = await endereco_elem.inner_text()

            # Anunciante — busca por seletores CSS com múltiplos fallbacks
            advertiser = await self._extract_advertiser(page)
            if advertiser.get("nome"):
                details["anunciante"] = advertiser["nome"]
            if advertiser.get("tipo"):
                details["anunciante_tipo"] = advertiser["tipo"]

            # Características do condomínio — busca em seções específicas do DOM
            caract_cond = await self._extract_condominium_features(page)
            if caract_cond:
                details["caracteristicas_condominio"] = caract_cond

            # Datas - formato: "Publicado há X meses , atualizado há Y horas."
            # ou: "Anúncio criado em DD de MÊS de AAAA, atualizado há X horas."

            # Data de publicação
            pub_patterns = [
                r'[Pp]ublicado\s+há\s+(\d+\s*(?:hora|horas|dia|dias|semana|semanas|mês|meses|ano|anos))',
                r'[Cc]riado\s+em\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
            ]
            for pattern in pub_patterns:
                pub_match = re.search(pattern, page_text)
                if pub_match:
                    details["data_publicacao"] = pub_match.group(1)
                    break

            # Data de atualização
            update_patterns = [
                r'atualizado\s+há\s+(\d+\s*(?:hora|horas|dia|dias|semana|semanas|mês|meses|ano|anos))',
            ]
            for pattern in update_patterns:
                upd_match = re.search(pattern, page_text, re.IGNORECASE)
                if upd_match:
                    details["data_atualizacao"] = upd_match.group(1)
                    break

        except Exception as e:
            logger.error(f"Erro ao extrair dados de detalhe: {e}")
            logger.error(traceback.format_exc())

        return details

    async def _extract_advertiser(self, page: Page) -> dict:
        """Extrai informações do anunciante via seletores CSS.

        Usa múltiplos seletores para resiliência contra mudanças no DOM.
        """
        result = {}

        # Seletores para o nome do anunciante (do mais específico ao mais genérico)
        name_selectors = [
            '[data-testid*="advertiser-name"]',
            '[data-testid*="advertiser"] h2',
            '[data-testid*="advertiser"] [class*="name"]',
            '[class*="AdvertiserName"]',
            '[class*="advertiser"] [class*="name"]',
        ]

        for selector in name_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = (await elem.inner_text()).strip()
                    if text and len(text) < 100:
                        result["nome"] = text
                        break
            except Exception:
                continue

        # Fallback: extrair do container inteiro do anunciante com regex
        if not result.get("nome"):
            try:
                container = await page.query_selector('[data-testid*="advertiser"]')
                if container:
                    text = await container.inner_text()
                    # Tenta extrair nome de imobiliária/corretor
                    match = re.search(
                        r'([A-ZÀ-Ú][a-zA-Zà-ú\s]+(?:Imóveis|Imobiliária|Corretor|Construtora))',
                        text,
                    )
                    if match:
                        result["nome"] = match.group(1).strip()
            except Exception:
                pass

        # Tipo do anunciante — extrair do container específico
        type_selectors = [
            '[data-testid*="advertiser-type"]',
            '[data-testid*="advertiser"] [class*="type"]',
            '[data-testid*="advertiser"] [class*="badge"]',
        ]

        for selector in type_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = (await elem.inner_text()).strip().lower()
                    if "imobiliária" in text or "creci" in text:
                        result["tipo"] = "Imobiliária"
                    elif "proprietário" in text or "particular" in text:
                        result["tipo"] = "Proprietário"
                    elif "incorporadora" in text or "construtora" in text:
                        result["tipo"] = "Incorporadora"
                    break
            except Exception:
                continue

        return result

    @staticmethod
    async def _is_cloudflare_blocked(page: Page) -> bool:
        """Detecta bloqueio do Cloudflare por indicadores específicos."""
        try:
            indicators = await page.evaluate("""
                () => ({
                    title: document.title,
                    hasCfChallenge: !!document.querySelector('#challenge-running, #cf-challenge-running'),
                    hasRayId: !!document.querySelector('.ray-id, [data-ray]'),
                    bodyText: (document.body.innerText || '').substring(0, 500),
                })
            """)

            title = indicators.get("title", "").lower()
            body = indicators.get("bodyText", "").lower()

            if indicators.get("hasCfChallenge") or indicators.get("hasRayId"):
                return True
            if "just a moment" in title or "attention required" in title:
                return True
            if "checking your browser" in body or "ray id" in body:
                return True

            return False
        except Exception:
            return False

    async def _extract_condominium_features(self, page: Page) -> List[str]:
        """Extrai características do condomínio de seções específicas do DOM.

        Busca em containers de amenities/features ao invés de texto livre,
        evitando falsos positivos de palavras que aparecem na descrição.
        """
        features = []

        # Seletores que apontam para seções de amenidades do ZapImóveis
        selectors = [
            '[data-testid*="amenities"] li',
            '[data-testid*="features"] li',
            '[class*="amenities"] li',
            '[class*="Features"] li',
            'section:has(h2:text-matches("Condomínio|Lazer|Comodidades", "i")) li',
        ]

        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    text = (await el.inner_text()).strip()
                    if text and len(text) < 60:
                        features.append(text)
                if features:
                    break
            except Exception:
                continue

        # Deduplica preservando ordem
        seen = set()
        unique = []
        for f in features:
            if f.lower() not in seen:
                seen.add(f.lower())
                unique.append(f)

        return unique

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
