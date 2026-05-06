class ExternalServiceError(RuntimeError):
    def __init__(self, service: str, message: str):
        self.service = service
        super().__init__(message)
