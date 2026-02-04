"""Extrator de dados diretamente do HTML via Playwright."""

import asyncio
import json
import logging
import random
import re
import traceback
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
            base_path = f"{ScraperConfig.BASE_URL}/venda/apartamentos/rj+rio-de-janeiro+zona-sul+leme/"
            url = base_path if page_num == 1 else f"{base_path}?pagina={page_num}"

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
                await asyncio.sleep(5)

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
        """Enriquece propriedades com dados das páginas de detalhe."""
        enriched = []
        total = len(properties)

        for i, prop in enumerate(properties):
            logger.info(f"Buscando detalhes {i+1}/{total}: {prop.id}")

            try:
                enriched_prop = await self._fetch_property_details(prop)
                enriched.append(enriched_prop)

                # Delay entre requisições
                if i < total - 1:
                    delay = random.uniform(1.0, 2.0)
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.warning(f"Erro ao buscar detalhes de {prop.id}: {e}")
                enriched.append(prop)

        return enriched

    async def _fetch_property_details(self, prop: Property) -> Property:
        """Busca dados adicionais da página de detalhe do imóvel."""
        page = await self._context.new_page()

        try:
            await page.goto(prop.url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)

            # Verifica se página carregou corretamente (não é Cloudflare challenge)
            page_text = await page.evaluate("() => document.body.innerText")
            if len(page_text) < 1000:
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

            # Anunciante - extrair do elemento com data-testid que contém "advertiser"
            advertiser_elem = await page.query_selector('[data-testid*="advertiser"]')
            if advertiser_elem:
                advertiser_text = await advertiser_elem.inner_text()
                # Formato concatenado: "Anunciante PremiumOrla Rio ImóveisAnunciante verificado..."
                # Extrair entre "Premium" e "Anunciante verificado"
                anunc_match = re.search(r'Premium([A-Za-zÀ-ú\s]+?)(?:Anunciante|Creci|Este)', advertiser_text)
                if anunc_match:
                    details["anunciante"] = anunc_match.group(1).strip()
                else:
                    # Fallback: busca padrão "Nome Imóveis"
                    name_match = re.search(r'([A-Z][a-zA-Zá-ú\s]+(?:Imóveis|Imobiliária|Corretor))', advertiser_text)
                    if name_match:
                        details["anunciante"] = name_match.group(1).strip()

            # Fallback para anunciante no texto da página
            if not details.get("anunciante"):
                # Busca padrão "Nome Imóveis" ou similar na página completa
                anunc_match = re.search(r'([A-Z][a-zA-Zá-ú\s]+(?:Imóveis|Imobiliária))', page_text)
                if anunc_match:
                    details["anunciante"] = anunc_match.group(1).strip()

            # Tipo de anunciante
            if "imobiliária" in page_text.lower() or "creci" in page_text.lower():
                details["anunciante_tipo"] = "Imobiliária"
            elif "proprietário" in page_text.lower() or "particular" in page_text.lower():
                details["anunciante_tipo"] = "Proprietário"
            elif "incorporadora" in page_text.lower():
                details["anunciante_tipo"] = "Incorporadora"

            # Características do condomínio
            caract_cond = []
            cond_features = [
                "Piscina", "Academia", "Salão de festas", "Churrasqueira",
                "Playground", "Sauna", "Quadra", "Portaria 24h", "Segurança",
                "Jardim", "Elevador", "Bicicletário", "Lavanderia",
            ]
            for feature in cond_features:
                if feature.lower() in page_text.lower():
                    caract_cond.append(feature)
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

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
