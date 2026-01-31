"""Retry com backoff exponencial."""

import random
import time
import logging
from functools import wraps
from typing import Callable, TypeVar, Any

import httpx

from config import ScraperConfig

logger = logging.getLogger("zapimoveis_scraper.retry")

T = TypeVar("T")


class RetryExhausted(Exception):
    """Exceção quando todas as tentativas falharam."""

    pass


def retry_with_backoff(
    max_retries: int = ScraperConfig.MAX_RETRIES,
    base_delay: float = ScraperConfig.BASE_DELAY,
    max_delay: float = ScraperConfig.MAX_DELAY,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.ReadTimeout,
        ConnectionError,
        TimeoutError,
    ),
    retryable_status_codes: tuple = (429, 500, 502, 503, 504),
) -> Callable:
    """
    Decorator para retry com backoff exponencial.

    Delays:
    - Tentativa 1: 1s
    - Tentativa 2: 2s
    - Tentativa 3: 4s
    - Tentativa 4: 8s
    - Tentativa 5: 16s (ou max_delay)

    Com jitter: adiciona variação aleatória ±20%
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(1, max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # Verifica status code se for Response
                    if isinstance(result, httpx.Response):
                        if result.status_code in retryable_status_codes:
                            raise httpx.HTTPStatusError(
                                f"Status {result.status_code}",
                                request=result.request,
                                response=result,
                            )

                    return result

                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(
                            f"Todas as {max_retries} tentativas falharam: {e}"
                        )
                        raise RetryExhausted(
                            f"Falha após {max_retries} tentativas"
                        ) from e

                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)

                    if jitter:
                        jitter_range = delay * 0.2
                        delay = delay + random.uniform(-jitter_range, jitter_range)

                    logger.warning(
                        f"Tentativa {attempt}/{max_retries} falhou: {e}. "
                        f"Aguardando {delay:.2f}s antes de retry..."
                    )
                    time.sleep(delay)

                except httpx.HTTPStatusError as e:
                    if e.response.status_code in retryable_status_codes:
                        last_exception = e
                        if attempt == max_retries:
                            logger.error(
                                f"Todas as {max_retries} tentativas falharam: {e}"
                            )
                            raise RetryExhausted(
                                f"Falha após {max_retries} tentativas"
                            ) from e

                        delay = min(
                            base_delay * (exponential_base ** (attempt - 1)), max_delay
                        )

                        if jitter:
                            jitter_range = delay * 0.2
                            delay = delay + random.uniform(-jitter_range, jitter_range)

                        logger.warning(
                            f"Tentativa {attempt}/{max_retries} - Status {e.response.status_code}. "
                            f"Aguardando {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        raise

            raise RetryExhausted(f"Falha após {max_retries} tentativas") from last_exception

        return wrapper

    return decorator


def retry_with_backoff_async(
    max_retries: int = ScraperConfig.MAX_RETRIES,
    base_delay: float = ScraperConfig.BASE_DELAY,
    max_delay: float = ScraperConfig.MAX_DELAY,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.ReadTimeout,
        ConnectionError,
        TimeoutError,
    ),
    retryable_status_codes: tuple = (429, 500, 502, 503, 504),
) -> Callable:
    """Versão assíncrona do retry com backoff."""
    import asyncio

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(1, max_retries + 1):
                try:
                    result = await func(*args, **kwargs)

                    if isinstance(result, httpx.Response):
                        if result.status_code in retryable_status_codes:
                            raise httpx.HTTPStatusError(
                                f"Status {result.status_code}",
                                request=result.request,
                                response=result,
                            )

                    return result

                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(
                            f"Todas as {max_retries} tentativas falharam: {e}"
                        )
                        raise RetryExhausted(
                            f"Falha após {max_retries} tentativas"
                        ) from e

                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)), max_delay
                    )

                    if jitter:
                        jitter_range = delay * 0.2
                        delay = delay + random.uniform(-jitter_range, jitter_range)

                    logger.warning(
                        f"Tentativa {attempt}/{max_retries} falhou: {e}. "
                        f"Aguardando {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)

                except httpx.HTTPStatusError as e:
                    if e.response.status_code in retryable_status_codes:
                        last_exception = e
                        if attempt == max_retries:
                            logger.error(
                                f"Todas as {max_retries} tentativas falharam: {e}"
                            )
                            raise RetryExhausted(
                                f"Falha após {max_retries} tentativas"
                            ) from e

                        delay = min(
                            base_delay * (exponential_base ** (attempt - 1)), max_delay
                        )

                        if jitter:
                            jitter_range = delay * 0.2
                            delay = delay + random.uniform(-jitter_range, jitter_range)

                        logger.warning(
                            f"Tentativa {attempt}/{max_retries} - Status {e.response.status_code}. "
                            f"Aguardando {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise

            raise RetryExhausted(
                f"Falha após {max_retries} tentativas"
            ) from last_exception

        return wrapper

    return decorator
