import logging
from typing import List, Optional, Type, TypeVar

from Cerberus.exceptions import ExecutionError
from Cerberus.plugins.basePlugin import BasePlugin
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment
from Cerberus.plugins.products.baseProduct import BaseProduct

from .baseTestResult import BaseTestResult

T = TypeVar("T", bound=BaseEquipment)


class BaseTest(BasePlugin):
    def __init__(self, name, description: Optional[str] = None):
        super().__init__(name, description)
        self.result: BaseTestResult | None = None
        self.requiredEquipment: List[Type[BaseEquipment]] = []
        self._equipment: dict[type[BaseEquipment], BaseEquipment] = {}
        self.product: BaseProduct | None = None

    def setProduct(self, product: BaseProduct) -> None:
        """Inject the product-under-test (already initialised/configured)."""
        self.product = product

    def getProduct(self) -> BaseProduct:
        """Return injected product or raise if missing."""
        if self.product is None:
            raise RuntimeError("No product injected into test")

        return self.product

    def initialise(self, init=None) -> bool:
        logging.debug("Initialise")
        if init is not None:
            self._init = init

        self._initialised = True
        return True

    def configure(self, config=None) -> bool:
        logging.debug("Configure")
        if config is not None:
            self.config = config

        self.configured = True
        return True

    def finalise(self) -> bool:
        logging.debug("Finalise")
        self.finalised = True
        return True

    def _addRequirements(self, typeNames):
        self.requiredEquipment.extend(typeNames)

    def provideEquip(self, equipment: dict[type[BaseEquipment], BaseEquipment]) -> None:
        """Inject resolved equipment instances keyed by their required types."""
        self._equipment = dict(equipment)

    def getEquip(self, equip_type: Type[T]) -> T | None:
        """Retrieve an injected equipment instance by its type."""
        inst = self._equipment.get(equip_type)
        return inst if isinstance(inst, equip_type) else None

    def run(self):
        if self.product is None:
            raise ExecutionError("There is no product provided for test (DUT)")

        logging.info(f"Running test: {self.name}")

    def stop(self):
        logging.info(f"Stopping test: {self.name}")

    def getResult(self) -> BaseTestResult | None:
        return self.result
