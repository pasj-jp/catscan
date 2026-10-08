from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import io


class BasePaperChecker(ABC):
    """
    Abstract base class for all paper format checkers (Word / LaTeX, JACoW / PASJ).
    """

    @abstractmethod
    def validate(
        self,
        file_source: Union[str, bytes, io.BytesIO],
        filename: str = "document.docx",
        conference_id: Optional[Union[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Validate the document formatting and return a structured report dictionary.
        """
        pass
