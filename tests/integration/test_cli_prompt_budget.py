"""SC-001 prompt-budget test for the milling REPL flow (T023a).

SC-001 caps a complete end-milling run at **14** prompts, of which at most
**12** require the user to type a value.
``contracts/cli-repl-milling.md`` "Prompt-count budget" specifies the actual
flow as 13 prompts / 12 typed.

The exact-count assertions below are a deliberate tripwire: the *binding*
requirement is SC-001's ceiling, so a change that legitimately adds a prompt
must update this test **and** re-check SC-001, rather than letting the count
drift silently up to (or past) the limit.
"""

import builtins

from machine_calc.cli import run

#: SC-001's ceiling.
SC001_MAX_PROMPTS = 14
SC001_MAX_TYPED_VALUES = 12

#: The exact counts the current flow is contracted to issue.
CONTRACT_PROMPT_COUNT = 13
CONTRACT_TYPED_VALUE_COUNT = 12

_END_MILLING_ANSWERS = [
    "milling",
    "end milling",
    "metric",
    "Metal",
    "Mild Steel",
    "Carbide",
    "10",
    "2",
    "5",
    "0.05",
    "4",
    "100",
    "",  # optional power rating -- dismissible with a bare Enter
]


def _run_and_count(monkeypatch, answers):
    prompts = []
    supply = iter([*answers, "n"])

    def _input(prompt=""):
        prompts.append(prompt)
        return next(supply)

    monkeypatch.setattr(builtins, "input", _input)
    run()
    # Exclude the trailing "run another calculation?" prompt, which is not
    # part of a single calculation run.
    return prompts[:-1]


def test_end_milling_issues_exactly_the_contracted_number_of_prompts(monkeypatch, capsys):
    prompts = _run_and_count(monkeypatch, _END_MILLING_ANSWERS)
    capsys.readouterr()

    assert len(prompts) == CONTRACT_PROMPT_COUNT
    assert len(prompts) <= SC001_MAX_PROMPTS


def test_at_most_twelve_prompts_require_a_typed_value(monkeypatch, capsys):
    prompts = _run_and_count(monkeypatch, _END_MILLING_ANSWERS)
    capsys.readouterr()

    typed = [prompt for prompt, answer in zip(prompts, _END_MILLING_ANSWERS) if answer != ""]

    assert len(typed) == CONTRACT_TYPED_VALUE_COUNT
    assert len(typed) <= SC001_MAX_TYPED_VALUES


def test_the_dismissible_prompt_is_the_optional_power_rating(monkeypatch, capsys):
    """The one non-typed prompt must be the *optional* input, not a required one."""

    prompts = _run_and_count(monkeypatch, _END_MILLING_ANSWERS)
    capsys.readouterr()

    dismissed = [prompt for prompt, answer in zip(prompts, _END_MILLING_ANSWERS) if answer == ""]

    assert len(dismissed) == 1
    assert "Available power" in dismissed[0]


def test_face_milling_stays_within_the_same_budget(monkeypatch, capsys):
    """Face milling has the same shape, so it must not exceed the ceiling."""

    prompts = _run_and_count(
        monkeypatch,
        [
            "milling",
            "face milling",
            "metric",
            "Metal",
            "Mild Steel",
            "Carbide",
            "50",
            "1.5",
            "40",
            "0.15",
            "5",
            "200",
            "",
        ],
    )
    capsys.readouterr()

    assert len(prompts) == CONTRACT_PROMPT_COUNT
    assert len(prompts) <= SC001_MAX_PROMPTS
