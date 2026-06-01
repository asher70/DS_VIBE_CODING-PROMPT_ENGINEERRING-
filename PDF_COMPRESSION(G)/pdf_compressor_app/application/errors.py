from __future__ import annotations


class ApplicationError(Exception):
    """An error that can be shown directly to the user."""

    def __init__(self, title: str, message: str) -> None:
        super().__init__(message)
        self.title = title
        self.message = message


class MissingFileError(ApplicationError):
    """Raised when the selected input PDF cannot be found."""


class InvalidInputError(ApplicationError):
    """Raised when the selected input is not a usable PDF."""


class SaveLocationError(ApplicationError):
    """Raised when the selected save location is not usable."""


class CompressionFailedError(ApplicationError):
    """Raised when compression fails."""

