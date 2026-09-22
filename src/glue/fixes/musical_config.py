"""Central V0.5 edit permissions, movement limits, and objective calibration."""

from dataclasses import dataclass
from math import isfinite

from .minimal import RepairPreset


@dataclass(frozen=True)
class EditPermissions:
    pitch: bool = True
    timing: bool = False
    duration: bool = False

    def __post_init__(self) -> None:
        if any(not isinstance(v, bool) for v in (self.pitch, self.timing, self.duration)):
            raise TypeError("edit permissions must be bools")


@dataclass(frozen=True)
class MusicalWeights:
    harmony: float = 1.0
    resolution: float = 4.0
    melody: float = 1.5
    voice_leading: float = 0.8
    bass: float = 0.4
    rhythm: float = 6.0
    register: float = 0.8
    collision: float = 12.0
    unison: float = 3.0
    motif: float = 5.0
    motif_consistency: float = 0.7
    contour: float = 1.5
    groove: float = 5.0
    edit: float = 0.25
    pitch_distance: float = 0.08
    onset_distance: float = 1.5
    duration_distance: float = 1.0
    preservation: float = 8.0

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True)
class MusicalSearch:
    preset: RepairPreset
    max_edits: int
    note_pool: int
    pitch_range: int
    beam: int
    depth: int
    evaluations: int
    onset_beats: float
    duration_beats: float
    duration_fraction: float
    alternatives: int = 3
    grid_beats: float = 0.125
    weights: MusicalWeights = MusicalWeights()


def musical_search_for(preset: RepairPreset | str = RepairPreset.MINIMAL) -> MusicalSearch:
    preset = RepairPreset(preset)
    if preset is RepairPreset.MINIMAL:
        return MusicalSearch(preset, 2, 6, 2, 4, 2, 100, 0.125, 0.125, 0.25)
    if preset is RepairPreset.BALANCED:
        return MusicalSearch(preset, 4, 10, 4, 7, 3, 220, 0.25, 0.5, 0.5)
    return MusicalSearch(preset, 8, 16, 7, 10, 4, 420, 0.5, 1.0, 0.75)
