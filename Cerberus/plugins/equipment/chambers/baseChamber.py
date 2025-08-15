from Cerberus.plugins.equipment.baseCommsEquipment import BaseCommsEquipment


class BaseChamber(BaseCommsEquipment):
    """
    Base class for all chamber equipment plugins.
    This class should be extended by specific chamber equipment plugins.
    """

    def __init__(self, name: str):
        super().__init__(name)
        self.temperature = 0.0

    def getTemperature(self) -> float:
        return self.temperature  # Placeholder for temperature retrieval logic

    def setTemperature(self, temperature: float):
        """
        Sets the current temperature of the chamber.
        """
        self.temperature = temperature
