from pydantic import BaseModel
from loguru import logger
from functools import wraps
import httpx
import time
import sqlite3
import random

class RemoteUser(BaseModel):
    id: int
    name: str
    username: str
    email: str

class User(BaseModel):
    id: int
    name: str
    username: str
    email: str
    age: int

def cache(ttl_seconds: float):
    """Кэширует результат вызова функции fetch_remote_users
    Args:
        ttl_seconds (float): время на которое кэширует результат fetch_remote_users
    """
    def decorator(func):
        cache_storage = {}
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal cache_storage
            key = (args, tuple(sorted(kwargs.items())))

            if key in cache_storage:
                (cache_result, cache_time) = cache_storage[key]
                if (time.time() - cache_time) < ttl_seconds:
                    logger.debug(f"Использован кэш")
                    return cache_result
        
            result = func(*args, **kwargs)
            cache_storage[key] = (result, time.time())
            logger.debug(f"Кэш обновлен")

            return result
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

class UserRepository:
    def __init__(self, db_path: str = "/home/TvoiiSon/Data/Work/IBS/Python/FirstProj/other/user.db"):
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self.db_path = db_path

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                age INTEGER
            )
        """)
        self.connection.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.connection.close()

    def __repr__(self):
        count_users = self.cursor.execute("""
            SELECT COUNT(*) FROM users
        """).fetchone()[0]
        return f"UserRepository(db_path={self.db_path}, users={count_users})"

    @retry(exceptions=sqlite3.OperationalError)
    @timing()
    def create_user(self, name: str, username: str, email: str, age: int) -> User | None:
        quary = "INSERT INTO users (name, username, email, age) VALUES (?, ?, ?, ?)"

        try:
            self.cursor.execute(quary, (name, username, email, age))
            self.connection.commit()
        except sqlite3.IntegrityError as e:
            logger.error(f"Такой пользователь существует - {e}")
            return None
        
        new_id = self.cursor.lastrowid
        if new_id:
            logger.info(f"Вставка прошла успешно id - {new_id}")
            return User(id=new_id, name=name, username=username, email=email, age=age)
        
    def get_user(self, user_id: int) -> User | None:
        quary = "SELECT * FROM users WHERE id = ?"
        result = self.cursor.execute(quary, (user_id,)).fetchone()

        if result is not None:
            logger.info(f"Пользователь с таким id - {user_id}, найден username - {result[1]}")
            return User(id=result[0], name=result[1], username=result[2], email=result[3], age=result[4])
        else:
            logger.warning(f"Пользователя с таким id - {user_id}, не существует")
            return None

    @timing()
    def get_all_users(self) -> list[User]:
        result = self.cursor.execute("""
            SELECT * FROM users ORDER BY id DESC
        """).fetchall()

        users = [User(id=row[0], name=row[1], username=row[2], email=row[3], age=row[4]) for row in result]
        logger.info(f"Найдено пользователей: {len(users)}")

        return users

    @retry(exceptions=sqlite3.OperationalError)
    def delete_user(self, user_id: int) -> bool:
        query = "DELETE FROM users WHERE id = ?"
        self.cursor.execute(query, (user_id,))
        self.connection.commit()

        if self.cursor.rowcount > 0:
            logger.info(f"Пользователь с id {user_id} удален")
            return True
        else:
            logger.warning(f"Пользователь с id {user_id} не найден для удаления")
            return False

@cache(ttl_seconds=30)
def fetch_remote_users(client: httpx.Client) -> list[RemoteUser]:
    result = []
    try:
        response = client.get("/users").json()
        for r in response:
            result.append(RemoteUser(**r))
    except httpx.RequestError as e:
        logger.opt(exception=True).warning(f"Проблема с запросом пользователей: {e}")

    return result

def sync_users_to_db(repo: UserRepository, remote_users: list[RemoteUser]) -> dict[str, int]:
    count_create = 0
    count_skipped = 0     
    for user in remote_users:
        create_result = repo.create_user(name=user.name, username=user.username, email=user.email, age=random.randint(18, 65))

        if create_result == None: 
            count_skipped += 1
        else:
            count_create += 1

    return {"created": count_create, "skipped": count_skipped}

if __name__ == "__main__":
    with httpx.Client(base_url="https://jsonplaceholder.typicode.com") as client, UserRepository() as user_repo:
        remote_users = fetch_remote_users(client)
        fetch_remote_users(client)

        print(sync_users_to_db(user_repo, remote_users))