"""Service-boundary errors: no user secrets, URLs, or raw subprocess stderr."""
class FeatureUnavailable(RuntimeError):
    """The backend has not been implemented; do not pretend to queue or save."""
