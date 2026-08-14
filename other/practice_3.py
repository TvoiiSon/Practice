from pydantic import BaseModel
from loguru import logger
from functools import wraps
import time
import sqlite3

class User(BaseModel):
    id: int
    username: str
    email: str
    age: int

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
    def __init__(self, db_path: str = "user.db"):
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self.db_path = db_path

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    def create_user(self, username: str, email: str, age: int) -> User | None:
        quary = "INSERT INTO users (username, email, age) VALUES (?, ?, ?)"

        try:
            self.cursor.execute(quary, (username, email, age))
            self.connection.commit()
        except sqlite3.IntegrityError as e:
            logger.error(f"Такой пользователь существует - {e}")
            return None
        
        new_id = self.cursor.lastrowid
        if new_id:
            logger.info(f"Вставка прошла успешно id - {new_id}")
            return User(id=new_id, username=username, email=email, age=age)
        
    def get_user(self, user_id: int) -> User | None:
        quary = "SELECT * FROM users WHERE id = ?"
        result = self.cursor.execute(quary, (user_id,)).fetchone()

        if result is not None:
            logger.info(f"Пользователь с таким id - {user_id}, найден username - {result[1]}")
            return User(id=result[0], username=result[1], email=result[2], age=result[3])
        else:
            logger.warning(f"Пользователя с таким id - {user_id}, не существует")
            return None

    @timing()
    def get_all_users(self) -> list[User]:
        result = self.cursor.execute("""
            SELECT * FROM users ORDER BY id DESC
        """).fetchall()

        users = [User(id=row[0], username=row[1], email=row[2], age=row[3]) for row in result]
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

if __name__ == "__main__":
    with UserRepository("/home/TvoiiSon/Data/Work/IBS/Python/FirstProj/other/test_users.db") as user_repo:
        # создание пользователей
        user_repo.create_user("alice", "alice@test.com", 30)
        user_repo.create_user("bob", "bob@test.com", 22)
        user_repo.create_user("carol", "carol@test.com", 27)

        # попытка создать уже существующего пользователя
        print(user_repo.create_user("carol", "carol@test.com", 27))

        # получение существующего пользователя
        print(user_repo.get_user(1))

        # получение несуществующего пользователя
        print(user_repo.get_user(999))

        # получение всех пользователей
        print(user_repo.get_all_users())

        # удаление существующего пользователя
        print(user_repo.delete_user(1))

        # удаление несуществующего пользователя
        print(user_repo.delete_user(1))

        print(repr(user_repo))