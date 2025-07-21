from plugins import hookimpl, singleton
from plugins.equipment.spectrumAnalysers.baseSpecAnalyser import BaseSpecAnalyser

@hookimpl
@singleton
def createEquipmentPlugin():
    return BB60CEquipment()

class BB60CEquipment(BaseSpecAnalyser):
    def __init__(self):
        super().__init__("BB60C Spectrum Analyser")