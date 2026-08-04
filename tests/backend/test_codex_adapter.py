from replaytutor.adapters.agents.codex import CODEX_TUTOR_PROMPT
from replaytutor.modules.tutor.runtime import INSTRUCTIONS


def test_codex_prompt_requires_the_two_evidence_files_without_banning_reads() -> None:
    assert "read TUTOR_INSTRUCTIONS.md" in CODEX_TUTOR_PROMPT
    assert "tutor_context.json" in CODEX_TUTOR_PROMPT
    assert "required and explicitly permitted" in CODEX_TUTOR_PROMPT
    assert "Do not run tools" not in CODEX_TUTOR_PROMPT
    assert "Do not inspect any other path" in CODEX_TUTOR_PROMPT


def test_tutor_instructions_answer_environment_questions_without_a_trade_plan() -> None:
    assert "Answer the user's actual question directly" in INSTRUCTIONS
    assert "do not require a trading plan" in INSTRUCTIONS
