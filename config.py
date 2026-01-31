"""Configurações do scraper ZapImóveis."""

from pathlib import Path


class ScraperConfig:
    """Configurações centralizadas do scraper."""

    # URLs
    BASE_URL = "https://www.zapimoveis.com.br"
    API_URL = "https://glue-api.zapimoveis.com.br/v2/listings"

    # Localização (fixo para Leme)
    NEIGHBORHOOD = "Leme"
    CITY = "Rio de Janeiro"
    ZONE = "Zona Sul"
    LAT = "-22.961655"
    LON = "-43.165463"

    # Paginação
    PAGE_SIZE = 30  # Schema.org retorna 30 por página
    MAX_ITEMS = 100
    MAX_PAGES = 5  # 100 / 30 ≈ 4 páginas

    # Browser
    HEADLESS = True

    # Retry
    MAX_RETRIES = 5
    BASE_DELAY = 1.0
    MAX_DELAY = 60.0

    # Rate limiting
    REQUEST_DELAY_MIN = 1.0
    REQUEST_DELAY_MAX = 3.0

    # Output
    OUTPUT_DIR = Path(__file__).parent / "output"
    CSV_FILENAME = "imoveis_leme.csv"
    JSON_FILENAME = "imoveis_leme.json"
    LOG_FILENAME = "scraper.log"

    # Headers base
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    @classmethod
    def get_api_params(cls, page: int = 1) -> dict:
        """Retorna parâmetros para requisição da API."""
        from_index = (page - 1) * cls.PAGE_SIZE
        return {
            "business": "SALE",
            "listingType": "USED",
            "addressCity": cls.CITY,
            "addressZone": cls.ZONE,
            "addressNeighborhood": cls.NEIGHBORHOOD,
            "addressPointLat": cls.LAT,
            "addressPointLon": cls.LON,
            "addressType": "neighborhood",
            "unitTypes": "APARTMENT",
            "unitTypesV3": "APARTMENT",
            "usageTypes": "RESIDENTIAL",
            "page": page,
            "size": cls.PAGE_SIZE,
            "from": from_index,
            "includeFields": "search,listings",
        }

    @classmethod
    def get_headers(cls) -> dict:
        """Retorna headers para requisição."""
        return {
            "User-Agent": cls.USER_AGENT,
            "Referer": f"{cls.BASE_URL}/",
            "Origin": cls.BASE_URL,
            "Accept": "application/json",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "x-domain": ".zapimoveis.com.br",
        }
