class CatScanError(Exception):
    status_code: int = 400

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


class DocumentError(CatScanError):
    status_code: int = 400


class TemplateMismatchError(DocumentError):
    status_code: int = 409

    def __init__(self, selected: str, detected: str):
        self.selected = selected
        self.detected = detected
        super().__init__(f"The manuscript appears to use {detected.upper()}. Confirm the template before scanning.")


class AuthenticationError(CatScanError):
    status_code: int = 401


class ReportNotFoundError(CatScanError):
    status_code: int = 404


class IndicoAPIError(CatScanError):
    status_code: int = 502
