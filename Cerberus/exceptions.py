class CerberusException(Exception):
    """Base class for all Cerberus exceptions."""
    def __init__(self, message: str, *args, **kwargs):
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        return f"CerberusException: {self.message}"

class PluginError(CerberusException):
    """Custom exception raised for errors related to plugins in Cerberus."""
    def __init__(self, message: str, *args, **kwargs):
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        return f"Cerberus.PluginError: {self.message}"

class TestError(PluginError):
    """Custom exception raised for errors during test execution in Cerberus."""
    def __init__(self, message: str, *args, **kwargs):
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        return f"Cerberus.TestError: {self.message}"
        
class EquipmentError(PluginError):
    """Custom exception raised for errors related to equipment plugins in Cerberus."""
    def __init__(self, message: str, *args, **kwargs):
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        return f"Cerberus.EquipmentError: {self.message}"

class ExecutionError(CerberusException):
    """Custom exception raised for errors during test execution in Cerberus."""
    def __init__(self, message: str, *args, **kwargs):
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        return f"Cerberus.ExecutionError: {self.message}"