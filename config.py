"""Configurações do scraper ZapImóveis."""

from pathlib import Path


class ScraperConfig:
    """Configurações centralizadas do scraper."""

    # URLs
    BASE_URL = "https://www.zapimoveis.com.br"

    # Localização padrão
    NEIGHBORHOOD = "Leme"
    CITY = "Rio de Janeiro"
    STATE = "RJ"
    ZONE = "Zona Sul"

    # Busca
    SEARCH_TERM = ""  # Termo de busca livre (ex: "Rua Gustavo Sampaio")

    # Paginação
    PAGE_SIZE = 30
    MAX_ITEMS = 100
    MAX_PAGES = 5

    # Browser
    HEADLESS = True

    # Rate limiting
    REQUEST_DELAY_MIN = 1.0
    REQUEST_DELAY_MAX = 3.0

    # Paralelismo no enriquecimento de detalhes
    DETAIL_CONCURRENCY = 3

    # Imagens
    MAX_IMAGES = 10

    # Output
    OUTPUT_DIR = Path(__file__).parent / "output"
    CSV_FILENAME = "imoveis.csv"
    JSON_FILENAME = "imoveis.json"
    LOG_FILENAME = "scraper.log"

    # Headers base
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    @classmethod
    def get_search_url(cls, page_num: int = 1) -> str:
        """Constrói a URL de busca baseada na configuração atual."""
        city_slug = cls.CITY.lower().replace(" ", "-")
        state_slug = cls.STATE.lower()
        zone_slug = cls.ZONE.lower().replace(" ", "-")
        neighborhood_slug = cls.NEIGHBORHOOD.lower().replace(" ", "-")

        base_path = (
            f"{cls.BASE_URL}/venda/apartamentos/"
            f"{state_slug}+{city_slug}+{zone_slug}+{neighborhood_slug}/"
        )

        params = []
        if page_num > 1:
            params.append(f"pagina={page_num}")
        if cls.SEARCH_TERM:
            params.append(f"busca={cls.SEARCH_TERM.replace(' ', '+')}")

        return f"{base_path}?{'&'.join(params)}" if params else base_path
