from typing import Optional
import httpx
from loguru import logger
from pydantic import BaseModel, ValidationError

class Post(BaseModel):
    id: int
    userId: int
    title: str
    body: str

def fetch_resource(resource_id: int, timeout: Optional[float] = None) -> Post | None:
    url = f"https://jsonplaceholder.typicode.com/posts/{resource_id}"
    
    try:
        response = httpx.get(url, timeout=timeout)
    except httpx.RequestError as e:
        logger.opt(exception=True).warning(f"Проблема с запросом для {resource_id}: {e}")
        return None
    
    if response.status_code == 200:
        logger.info(f"Запись {resource_id} получена успешно")
        try:
            return Post(**response.json())
        except ValidationError as e:
            logger.error(f"Ошибка валидации ответа: {e}")
            return None
    elif response.status_code == 404:
        logger.error(f"Запись {resource_id} не найдена: {response.status_code} — {response.text}")
        return None
    else:
        logger.warning(f"Неожиданный статус {response.status_code} для записи {resource_id}: {response.text}")
        return None

if __name__ == "__main__":
    fetch_resource(resource_id=1)
    fetch_resource(resource_id=999)
    fetch_resource(resource_id=1, timeout=0.001)