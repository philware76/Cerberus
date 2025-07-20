class BaseTest:
    def __init__(self, name):
        self.name = name

    def run(self):
        print(f"Running test: {self.name}")

    def __str__(self):
        return self.name