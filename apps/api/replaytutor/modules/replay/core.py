from __future__ import annotations

import hashlib
from dataclasses import dataclass


class ReplayError(ValueError):
    pass


@dataclass(frozen=True)
class ReplayState:
    current_index: int
    start_index: int
    total_bars: int

    def __post_init__(self) -> None:
        if self.total_bars < 2:
            raise ReplayError("Replay requires at least two bars")
        if not 0 <= self.start_index <= self.current_index < self.total_bars:
            raise ReplayError("Replay indices are outside the dataset")


@dataclass(frozen=True)
class ReplayTransition:
    previous: ReplayState
    current: ReplayState
    advanced_bars: int
    reached_end: bool


def choose_start_index(
    *,
    total_bars: int,
    warmup_bars: int,
    start_mode: str,
    seed: int,
) -> int:
    minimum = warmup_bars - 1
    maximum = total_bars - 2
    if minimum > maximum:
        raise ReplayError("Dataset is too short for the requested warmup")
    if start_mode == "beginning":
        return minimum
    if start_mode != "random":
        raise ReplayError(f"Unsupported start mode: {start_mode}")
    digest = hashlib.sha256(f"replay-start:{seed}".encode()).digest()
    return minimum + int.from_bytes(digest[:8], "big") % (maximum - minimum + 1)


def advance(state: ReplayState, requested_bars: int) -> ReplayTransition:
    if requested_bars < 1:
        raise ReplayError("Advance amount must be positive")
    next_index = min(state.total_bars - 1, state.current_index + requested_bars)
    current = ReplayState(
        current_index=next_index,
        start_index=state.start_index,
        total_bars=state.total_bars,
    )
    return ReplayTransition(
        previous=state,
        current=current,
        advanced_bars=next_index - state.current_index,
        reached_end=next_index == state.total_bars - 1,
    )


def replay_fingerprint(
    *,
    snapshot_hash: str,
    seed: int,
    start_index: int,
    warmup_bars: int,
    engine_version: str = "replay-v1",
) -> str:
    material = (
        f"{engine_version}|{snapshot_hash}|{seed}|{start_index}|{warmup_bars}"
    )
    return hashlib.sha256(material.encode()).hexdigest()
