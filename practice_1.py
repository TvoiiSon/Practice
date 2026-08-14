class Cat:
    species = "кот"

    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.hunger = 50

    @staticmethod
    def meow():
        print("Мяу!")
    
    def feed(self, amount):
        if self.hunger - amount < 0:
            self.hunger = 0
        else:
            self.hunger -= amount
    
    def is_hungry(self):
        if self.hunger > 20:
            return True
        
        return False
    
    @classmethod
    def get_species(cls):
        return cls.species
    
cat = Cat("Барсик", "red")

cat.meow()
cat.feed(10)
print(cat.is_hungry())
print(cat.get_species())