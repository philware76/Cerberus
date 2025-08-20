from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.cables.baseCalCable import BaseCalCable


@hookimpl
@singleton
def createEquipmentPlugin():
    return TXCalCable()


class TXCalCable(BaseCalCable):
    def __init__(self):
        super().__init__("TX")

        chebyshevCal = {'coeffs': [-1.6428745517712031, -0.9268797185108294, 0.08889800648217869, 0.014193256441656027, -0.0775110168859542,
                                   0.0508954077042115, -0.06768486059294578, 0.0383303526640644, -0.0433626897672139], 'domain': [100.0, 3500.0], 'window': [-1.0, 1.0]}

        self.loadChebyshev((chebyshevCal))
