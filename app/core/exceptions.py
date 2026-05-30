class PiPMError(Exception):
    """Base application error."""


class NotFoundError(PiPMError):
    """Resource not found."""


class InvalidSymbolError(PiPMError):
    """Symbol is invalid or not recognized by the data provider."""


class ProviderError(PiPMError):
    """External market data provider failure."""


class ValidationError(PiPMError):
    """Request or domain validation failure."""
