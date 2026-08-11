"""Domain errors for fail-closed AssetOS MOB behavior."""


class AssetOSError(Exception):
    """Base class for controlled implementation errors."""


class ValidationError(AssetOSError):
    """Input failed deterministic validation."""


class AuthorizationError(AssetOSError):
    """Actor lacks the requested governed authorization."""


class ConflictError(AssetOSError):
    """Requested operation conflicts with existing governed state."""


class NotFoundError(AssetOSError):
    """Requested governed record does not exist or is unavailable."""


class UncertainCommitError(AssetOSError):
    """Commit status is uncertain and must be reconciled before retry."""
