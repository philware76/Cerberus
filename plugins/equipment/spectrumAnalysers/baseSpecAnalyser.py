from plugins.equipment.baseEquipment import BaseEquipment

class BaseSpecAnalyser(BaseEquipment):
    """
    Base class for all spectrum analyser equipment plugins.
    This class should be extended by specific spectrum analyser equipment plugins.
    """

    def __init__(self, name: str):
        super().__init__(name)

