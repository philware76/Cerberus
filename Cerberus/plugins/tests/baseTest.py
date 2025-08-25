import io
import logging
from typing import List, Optional, Type, TypeVar

from Cerberus.exceptions import EquipmentError, ExecutionError
from Cerberus.plugins.basePlugin import BasePlugin
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment
from Cerberus.plugins.products.baseProduct import BaseProduct

from .baseTestResult import BaseTestResult

T = TypeVar("T", bound=BaseEquipment)


class BaseTest(BasePlugin):
    def __init__(self, name, description: Optional[str] = None, checkProduct: Optional[bool] = True):
        super().__init__(name, description)
        self.result: BaseTestResult = BaseTestResult(name)
        self.requiredEquipment: List[Type[BaseEquipment]] = []
        self._equipment: dict[type[BaseEquipment], BaseEquipment] = {}
        self.product: BaseProduct | None
        self.checkProduct = checkProduct

        self.setLogging()

    def setLogging(self):
        # set up per-test logger with in-memory buffer
        self.resultLogStream = io.StringIO()
        self.resultLogger = logging.getLogger(f"{self.name} Test")
        self.resultLogger.setLevel(logging.DEBUG)

        self.resultLogger.propagate = False

        self._log_handler = logging.StreamHandler(self.resultLogStream)
        self._log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
        self.resultLogger.addHandler(self._log_handler)

    def getLog(self):
        return self.resultLogStream.getvalue()

    def setProduct(self, product: BaseProduct | None) -> None:
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

        return True

    def finalise(self):
        logging.debug("Finalise")
        if self.result is not None:
            self.result.log = self.getLog()

        return True

    def _addRequirements(self, typeNames: List[Type[BaseEquipment]]) -> None:
        """Register required equipment types for this test.

        Each entry must be a class (not an instance) that ultimately derives
        from BaseEquipment. The executor / plugin service will locate concrete
        plugin instances satisfying these types (``isinstance`` check) and
        inject initialised instances prior to ``run``.
        """
        # Defensive: ignore accidental None or non-iterable input.
        if not typeNames:
            return

        self.requiredEquipment.extend(typeNames)

    def provideEquip(self, equipment: dict[type[BaseEquipment], BaseEquipment]) -> None:
        """Inject resolved equipment instances keyed by their required types."""
        self._equipment = dict(equipment)

    def getEquip(self, equip_type: Type[T]) -> T:
        """Retrieve an injected equipment instance by its type."""
        instrument = self._equipment.get(equip_type)
        instrument = instrument if isinstance(instrument, equip_type) else None
        if instrument is None:
            raise EquipmentError(f"Failed to find {equip_type.__name__}")

        return instrument

    def run(self):
        if self.checkProduct and self.product is None:
            raise ExecutionError("There is no product provided for test (DUT)")

        logging.info(f"Running test: {self.name}")

    def stop(self):
        logging.info(f"Stopping test: {self.name}")
