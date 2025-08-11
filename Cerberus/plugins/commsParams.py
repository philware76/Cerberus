from Cerberus.plugins.baseParameters import (BaseParameters, NumericParameter,
                                             StringParameter)


class CommsParams(BaseParameters):
    def __init__(self, commName: str = "Communication"):
        super().__init__(commName)

        self.addParameter(StringParameter("IP Address", "127.0.0.1", description="IP Address of the device"))
        self.addParameter(NumericParameter("Port", 5025, units="", minValue=0, maxValue=50000, description="Socket port number"))
        self.addParameter(NumericParameter("Timeout", 1000, units="ms", minValue=0, maxValue=10000, description="Communication timeout in milliseconds"))
