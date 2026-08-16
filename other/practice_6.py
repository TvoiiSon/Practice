from pydantic import BaseModel
from loguru import logger
from functools import wraps
import json
import httpx
import time
import asyncio

class TestCase(BaseModel):
    name: str
    user_id: int
    expected_status: int

class TestResult(BaseModel):
    name: str
    passed: bool
    actual_status: int | None
    error: str | None

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

class ScenarioRunner():
    def __init__(self, scenarios_path: str, base_url: str = "https://jsonplaceholder.typicode.com"):
        with open(scenarios_path, "r", encoding="utf-8") as file:
            scenario = json.load(file)

        self.base_url = base_url
        self.scenarios_path = scenarios_path
        self._scenarios = [TestCase(**item) for item in scenario]
        self._client = httpx.AsyncClient(base_url=base_url)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._client.aclose()

    def __repr__(self):
        return f"ScenarioRunner(scenarios_path={self.scenarios_path}, количество сценариев={len(self._scenarios)})"

    async def _check_scenario(self, scenario: TestCase) -> TestResult:
        try:
            response = await self._client.get(f"{self.base_url}/users/{scenario.user_id}")

            if response.status_code == scenario.expected_status:
                logger.info(f"Сценарий '{scenario.name}' прошел успешно, статус - {response.status_code}")
                return TestResult(name=scenario.name, passed=True, actual_status=response.status_code, error=None)
            else:
                logger.error(f"Сценарий '{scenario.name}' не прошёл: ожидали {scenario.expected_status}, получили {response.status_code}")
                return TestResult(name=scenario.name, passed=False, actual_status=response.status_code, error=f"Сценарий '{scenario.name}' не прошёл: ожидали {scenario.expected_status}, получили {response.status_code}")
        except httpx.RequestError as e:
            logger.opt(exception=True).warning(f"Проблема с запросом для пользователя с id - {scenario.user_id}: {e}")
            return TestResult(name=scenario.name, passed=False, actual_status=None, error=str(e))

    async def run(self) -> list[TestResult]:
        results = []

        for scenario in self._scenarios:
            sc = self._check_scenario(scenario)
            results.append(sc)

        results = await asyncio.gather(*results)

        return results

    @staticmethod
    def print_summary(list_res: list[TestResult]):
        passed_count = sum(1 for r in list_res if r.passed)
        logger.info(f"Пройдено: {passed_count} из {len(list_res)}")

        for r in list_res:
            if not r.passed:
                logger.info(f"Сценарий '{r.name}' не пройден из-за ошибки: {r.error}")

if __name__ == "__main__":
    async def test():
        async with ScenarioRunner(scenarios_path="/home/TvoiiSon/Data/Work/IBS/Python/FirstProj/other/scenarios.json") as scenario:
            res = await scenario.run()
            scenario.print_summary(res)

    asyncio.run(test())