from pydantic import BaseModel, ValidationError
from loguru import logger
from functools import wraps
import httpx
import time

class User(BaseModel):
    id: int
    name: str
    username: str
    email: str

class Post(BaseModel):
    id: int
    userId: int
    title: str
    body: str

def retry(max_attempts=3, delay=0.5, exceptions=(Exception,)):
    """Повторяет выполнение функции при возникновении указанных исключений.
    Args:
        max_attempts: максимальное число попыток
        delay: начальная задержка (сек)
        exceptions: кортеж исключений, которые перехватываем
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.opt(exception=True).warning(f"Все {max_attempts} попыток исчерпаны: {e}")
                        return None
                    logger.warning(f"Попытка {attempt} не удалась: {e}. Повтор через {current_delay}с")
                    time.sleep(current_delay)
            return None
        return wrapper
    return decorator

def timing(threshold=None):
    """Замеряет время выполнения функции.
    Args:
        threshold: если время превышает порог (сек), логируем как WARNING, иначе DEBUG
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            level = "WARNING" if threshold and elapsed > threshold else "DEBUG"
            logger.log(level, f"{func.__name__} выполнен за {elapsed:.4f} сек")
            return result
        return wrapper
    return decorator

class JSONPlaceholderClient:
    def __init__(self, base_url: str = "https://jsonplaceholder.typicode.com", timeout: float = 5.0):
        self._client = httpx.Client(base_url=base_url, timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._client.close()

    def __repr__(self):
        return f"JSONPlaceholderClient(base_url={self._client.base_url!r}, timeout={self._client.timeout!r})"

    @retry(exceptions=httpx.RequestError)
    @timing()
    def get_user(self, user_id: int) -> User | None:
        response = self._client.get(f"/users/{user_id}")

        if response.status_code == 200:
            logger.info(f"Запись {user_id} получена успешно")
            try:
                return User(**response.json())
            except ValidationError as e:
                logger.error(f"Ошибка валидации ответа: {e}")
                return None
        elif response.status_code == 404:
            logger.error(f"Запись {user_id} не найдена: {response.status_code} — {response.text}")
            return None
        else:
            logger.warning(f"Неожиданный статус {response.status_code} для записи {user_id}: {response.text}")
            return None

    @retry(exceptions=httpx.RequestError)
    @timing()
    def get_posts_by_user(self, user_id: int) -> list[Post]:
        response = self._client.get("/posts", params={"userId": user_id})

        if response.status_code == 200:
            logger.info(f"Запись {user_id} получена успешно")
            try:
                return [Post(**item) for item in response.json()]
            except ValidationError as e:
                logger.error(f"Ошибка валидации ответа: {e}")
                return []
        elif response.status_code == 404:
            logger.error(f"Запись {user_id} не найдена: {response.status_code} — {response.text}")
            return []
        else:
            logger.warning(f"Неожиданный статус {response.status_code} для записи {user_id}: {response.text}")
            return []

if __name__ == "__main__":
    with JSONPlaceholderClient() as client:
        print(client)
        client.get_user(1)
        client.get_posts_by_user(1)