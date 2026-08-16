from loguru import logger
from pydantic import BaseModel
import sqlite3
import itertools

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

class TestResult(BaseModel):
    name: str
    passed: bool
    actual_status: int | None
    error: str | None

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

    def get_all_users(self) -> list[User]:
        result = self.cursor.execute("""
            SELECT * FROM users ORDER BY id DESC
        """).fetchall()

        users = [User(id=row[0], name=row[1], username=row[2], email=row[3], age=row[4]) for row in result]
        logger.info(f"Найдено пользователей: {len(users)}")

        return users

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

def fetch_users_in_batches(repo:UserRepository, batch_size: int):
    _ = repo.cursor.execute("SELECT * FROM users ORDER BY id")
    while True:
        resp_user = repo.cursor.fetchmany(batch_size)
        if not resp_user:
            break
        else:
            yield [User(id=row[0], name=row[1], username=row[2], email=row[3], age=row[4]) for row in resp_user]

def id_generator(start: int = 1):
    while True:
        yield start
        start += 1

def iter_failed_only(results: list[TestResult]):
    for result in results:
        if not result.passed:
            yield result

if __name__ == "__main__":
    for row in itertools.islice(id_generator(), 5):
        print(row)