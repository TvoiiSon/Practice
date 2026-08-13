class Animal:
    def __init__(self, name, species):
        self.name = name
        self._species = species
        self.__age = 0
    
    def get_age(self):
        return self.__age
    
    def set_age(self, age):
        if age <= 0:
            print("Ошибка: возраст должен быть положительным")
        else:
            self.__age = age

    @staticmethod
    def voice():
        print("Звук")

class Cat(Animal):
    def __init__(self, name, color):
        self.color = color
        super().__init__(name, species = "Кошка")
    
    @staticmethod
    def voice():
        print("Мяу!")

    @staticmethod
    def purr():
        print("Мур-Мур...")   

class Dog(Animal):
    def __init__(self, name, breed):
        self.breed = breed
        super().__init__(name, species = "Собака")

    @staticmethod
    def voice():
        print("Гав!")

cat = Cat("Барсик", "Рыжий")
dog = Dog("Барбос", "Черный")

print(f"Кот: {cat.name}, цвет: {cat.color}, вид: {cat._species}")
print(f"Собака: {dog.name}, порода: {dog.breed}, вид: {dog._species}")

cat.voice()
cat.purr()

dog.voice()

cat.set_age(10)
print("Кот: ", cat.get_age())

dog.set_age(5)
print("Собака: ", dog.get_age())

dog.set_age(-10)