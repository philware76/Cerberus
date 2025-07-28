class TestError(Exception):
    """Custom exception raised for errors during test execution in Cerberus."""
    def __init__(self, message: str, *args, **kwargs):
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        return f"Cerberus.TestError: {self.message}"