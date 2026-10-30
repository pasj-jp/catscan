from typing import Protocol, Any


class Checker(Protocol):
    """
    Protocol for document format checkers.
    """

    def check(self, data: bytes, filename: str) -> dict[str, Any]:
        """
        Validate document content bytes and return a structured report dictionary.
        """
        ...
