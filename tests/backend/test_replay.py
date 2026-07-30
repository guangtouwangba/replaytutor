from __future__ import annotations

from replaytutor.modules.replay import (
    ReplayState,
    advance,
    choose_start_index,
    replay_fingerprint,
)


def test_replay_start_and_advance_are_deterministic() -> None:
    first = choose_start_index(
        total_bars=10_000,
        warmup_bars=120,
        start_mode="random",
        seed=42,
    )
    second = choose_start_index(
        total_bars=10_000,
        warmup_bars=120,
        start_mode="random",
        seed=42,
    )
    assert first == second
    assert 119 <= first <= 9_998

    state = ReplayState(current_index=first, start_index=first, total_bars=10_000)
    transition = advance(state, 25)
    assert transition.advanced_bars == 25
    assert transition.current.current_index == first + 25
    assert not transition.reached_end

    assert replay_fingerprint(
        snapshot_hash="a" * 64,
        seed=42,
        start_index=first,
        warmup_bars=120,
    ) == replay_fingerprint(
        snapshot_hash="a" * 64,
        seed=42,
        start_index=first,
        warmup_bars=120,
    )


def test_replay_never_advances_past_final_bar() -> None:
    state = ReplayState(current_index=98, start_index=20, total_bars=100)
    transition = advance(state, 500)
    assert transition.current.current_index == 99
    assert transition.advanced_bars == 1
    assert transition.reached_end
