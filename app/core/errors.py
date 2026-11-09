class DomainError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ExternalServiceError(DomainError):
    def __init__(self, message: str = "AI service temporarily unavailable"):
        super().__init__(message, 503)
