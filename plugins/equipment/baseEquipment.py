class BaseEquipment:
    def __init__(self, name):
        self.name = name
        self.initialised = False

    def Initialise(self) -> bool:
        print(f"Initialising equipment: {self.name}")
        self.initialised = True
        return True

    def getName(self) -> str:
        return self.name

    def isInitialised(self) -> bool:
        return self.initialised