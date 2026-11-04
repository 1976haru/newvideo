"""Provider ability matrix: capabilities, not promises of footage supply."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceCapability:
    name: str
    lane: str
    official_api: bool
    long_take_candidate: bool
    notes: str


CAPABILITIES: tuple[SourceCapability, ...] = (
    SourceCapability("Pexels", "short_composer", True, False,
                     "Pexels upload maximum 120s; do not promote 3-minute original availability."),
    SourceCapability("Pixabay", "short_composer", True, True,
                     "Verify response duration and real rendition; long files are not guaranteed."),
    SourceCapability("Wikimedia Commons", "long_original", True, True,
                     "Check videoinfo and file-specific rights."),
    SourceCapability("Internet Archive", "long_original", True, True,
                     "Check individual item media and license evidence."),
    SourceCapability("User Local", "long_original", False, True,
                     "Verify local file and user declaration of rights."),
)


def default_providers(long_original: bool = True) -> tuple[str, ...]:
    if long_original:
        return ("Wikimedia Commons", "Internet Archive", "User Local")
    return ("Pexels", "Pixabay", "User Local")
