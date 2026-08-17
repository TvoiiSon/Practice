from pydantic import BaseModel
from collections.abc import Callable

class TestCase(BaseModel):
    name: str
    user_id: int
    expected_status: int

class TestSuite():
    def __init__(self):
        self.list_cases: list[tuple[TestCase, list[str]]] = []

    def add_case(self, name: str, user_id: int, expected_status: int, tags: list[str] | None = None):
        if tags is None:
            tags = []
        if not any (t.startswith("status:") for t in tags):
            test_case = TestCase(name=name, user_id=user_id, expected_status=expected_status)
            tags.append(f"status:{expected_status}")
            self.list_cases.append((test_case, tags))
        else:
            test_case = TestCase(name=name, user_id=user_id, expected_status=expected_status)
            self.list_cases.append((test_case, tags))

    def build_status_checkers(self) -> list[Callable[[int], bool]]:
        unique_status = set()
        for case, _ in self.list_cases:
            unique_status.add(case.expected_status)

        operations_list: list[Callable[[int], bool]]  = []

        for status in unique_status:
            operations_list.append(lambda code, current_status=status: code == current_status)

        return operations_list

    def iter_cases_with_tag(self, tag: str):
        for case, case_tag in self.list_cases:
            if tag in case_tag:
                yield case.name 

    def count_and_list_tag(self, tag: str) -> tuple[int, list[str]]:
        names = list(self.iter_cases_with_tag(tag))
        return len(names), names

if __name__ == "__main__":
    suite = TestSuite()

    # без явных тегов — должен сработать автотег status:200 / status:404
    suite.add_case(name="Существующий пользователь", user_id=1, expected_status=200)
    suite.add_case(name="Другой существующий пользователь", user_id=2, expected_status=200)
    suite.add_case(name="Несуществующий пользователь", user_id=999, expected_status=404)

    # с явным тегом smoke — плюс автотег status:200, т.к. status: тега среди явных нет
    suite.add_case(name="Смоук-проверка", user_id=3, expected_status=200, tags=["smoke"])

    # с уже готовым тегом status: — автотег не должен добавляться повторно
    suite.add_case(name="Ручной статус-тег", user_id=4, expected_status=500, tags=["status:500", "regression"])

    print("--- Все кейсы и их теги ---")
    for case, tags in suite.list_cases:
        print(f"{case.name} (ожидание: {case.expected_status}) -> {tags}")

    print("\n--- Проверялки статусов ---")
    checkers = suite.build_status_checkers()
    print(f"Собрано проверялок: {len(checkers)}")
    for checker in checkers:
        print([checker(200), checker(404), checker(500)])

    print("\n--- count_and_list_tag ---")
    print("status:200 ->", suite.count_and_list_tag("status:200"))
    print("status:404 ->", suite.count_and_list_tag("status:404"))
    print("smoke ->", suite.count_and_list_tag("smoke"))
    print("несуществующий тег ->", suite.count_and_list_tag("no-such-tag"))