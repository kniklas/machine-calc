"""Shared dialog primitives and data-shaping helpers for the text GUI's screens.

Ports `console/cli.py`'s REPL-independent data-shaping logic (label building,
collision-safe reverse lookups, error rendering) unchanged (research.md #3),
and replaces its `input()`-based prompt functions with prompt-toolkit dialog
equivalents that loop/re-prompt the same way on invalid input. Reused by both
`screens/milling.py` and `screens/drilling.py` so neither duplicates this
logic (Constitution Principle I).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Callable

from prompt_toolkit.shortcuts import input_dialog, message_dialog, radiolist_dialog

from mfgparams import UnitSystem
from mfgparams.console.i18n import DEFAULT_LOCALE, has_message, translate
from mfgparams.models import CalculationMode, ErrorInfo
from mfgparams.processes.machining.drilling.tools import DrillingTool, get_tool
from mfgparams.processes.machining.milling._tool_registry import MillingTool
from mfgparams.registry import WorkpieceMaterial, get_material

UNIT_LABELS = {
    UnitSystem.METRIC: {
        "diameter": "mm",
        "depth": "mm",
        "feed_rate": "mm/min",
        "torque": "N·m",
        "power": "kW",
        "feed_per_tooth": "mm/tooth",
        "material_removal_rate": "cm³/min",
    },
    UnitSystem.IMPERIAL: {
        "diameter": "in",
        "depth": "in",
        "feed_rate": "in/min",
        "torque": "in-lb",
        "power": "HP",
        "feed_per_tooth": "in/tooth",
        "material_removal_rate": "in³/min",
    },
}

_MODE_OPTION_KEYS = {
    CalculationMode.STANDARD: "tui.mode.standard",
    CalculationMode.POWER_CONSTRAINED: "tui.mode.power_constrained",
    CalculationMode.FIXED_RPM: "tui.mode.fixed_rpm",
}


def _ok_cancel(locale: str, *, cancel_key: str = "tui.action.back") -> tuple[str, str]:
    return translate(locale, "tui.action.ok"), translate(locale, cancel_key)


def render_error(error: ErrorInfo, locale: str) -> str:
    """Render an :class:`ErrorInfo` for display, translating it if needed.

    Ported unchanged from `console/cli.py`'s `_render_error` (research.md #3)
    -- see that function's original docstring for the full rationale; the
    logic (not just the shape) is identical, only the caller changed.
    """

    if locale == DEFAULT_LOCALE or not has_message(locale, error.message_key):
        return error.message

    kwargs = dict(error.kwargs)
    label_key = kwargs.pop("label_key", None)
    if isinstance(label_key, str) and has_message(locale, label_key):
        kwargs["label"] = translate(locale, label_key)
    return translate(locale, error.message_key, **kwargs)


def display_label(
    entry: WorkpieceMaterial | DrillingTool | MillingTool,
    display_locale: str,
    message_locale: str,
) -> str:
    """Build a material/tool display label. Ported unchanged from
    `console/cli.py`'s `_display_label` (research.md #3)."""

    name = entry.display_name(display_locale)
    if entry.unit_system == "metric":
        return name
    return translate(
        message_locale, "tui.label.unit_system_suffix", name=name, unit_system=entry.unit_system
    )


def material_type_label(material_type: str, locale: str) -> str:
    """Ported unchanged from `console/cli.py`'s `_material_type_label`."""

    key = f"material_type.{material_type}"
    if has_message(locale, key):
        return translate(locale, key)
    fallback = material_type.replace("_", " ").replace("-", " ").title().strip()
    return fallback or material_type


def unique_labels(candidates: dict[str, str]) -> dict[str, str]:
    """Ported unchanged from `console/cli.py`'s `_unique_labels`."""

    collisions = Counter(candidates.values())
    taken: set[str] = set()
    unique: dict[str, str] = {}
    for key, label in candidates.items():
        candidate = f"{label} ({key})" if collisions[label] > 1 else label
        if candidate in taken:
            discriminator = 2
            while f"{candidate} #{discriminator}" in taken:
                discriminator += 1
            candidate = f"{candidate} #{discriminator}"
        taken.add(candidate)
        unique[key] = candidate
    return unique


# --- Dialog primitives -------------------------------------------------------


def ask_choice(
    *,
    title: str,
    label: str,
    options: dict[str, str],
    default: str | None,
    locale: str,
) -> str | None:
    """Show a radiolist of ``{value: display_label}`` and return the chosen
    value, or ``None`` if the user cancels ("go back")."""

    ok_text, cancel_text = _ok_cancel(locale)
    values = list(options.items())
    return radiolist_dialog(
        title=title,
        text=label,
        values=values,
        default=default if default in options else None,
        ok_text=ok_text,
        cancel_text=cancel_text,
    ).run()


def ask_number(
    *,
    title: str,
    label: str,
    unit: str,
    default: float | None,
    locale: str,
    validate: Callable[[float], ErrorInfo | None] | None = None,
) -> float | None:
    """Prompt for a required numeric value, re-prompting (via an error
    dialog, then re-showing the same original prompt) on a non-numeric or
    ``validate``-rejected entry. Returns ``None`` if the user cancels
    ("go back").

    Deliberately re-shows the *original* ``default`` on retry, not the
    rejected entry: prompt-toolkit's `TextArea` does not move the cursor to
    the end of pre-filled `default` text, so retyping a correction would
    insert *before* the invalid text rather than replacing it (found via a
    failing integration test: typing "10" to replace a rejected "0" silently
    produced "100"). This also matches `console/cli.py`'s own REPL
    behavior, which re-asked with the same original default rather than
    the invalid entry (FR-002 parity).
    """

    ok_text, cancel_text = _ok_cancel(locale)
    text = (
        translate(locale, "tui.prompt.number.with_default", label=label, unit=unit, default=default)
        if default is not None
        else translate(locale, "tui.prompt.number", label=label, unit=unit)
    )
    default_text = "" if default is None else str(default)

    while True:
        raw = input_dialog(
            title=title, text=text, default=default_text, ok_text=ok_text, cancel_text=cancel_text
        ).run()
        if raw is None:
            return None
        raw = raw.strip()
        if not raw and default is not None:
            return default
        try:
            value = float(raw)
        except ValueError:
            message_dialog(
                title=translate(locale, "tui.error.title"),
                text=translate(locale, "tui.prompt.number.invalid"),
                ok_text=ok_text,
            ).run()
            continue

        error = validate(value) if validate else None
        if error is None:
            return value
        message_dialog(
            title=translate(locale, "tui.error.title"),
            text=render_error(error, locale),
            ok_text=ok_text,
        ).run()


def ask_required_number(
    *,
    title: str,
    label: str,
    unit: str,
    default: float | None,
    locale: str,
    invalid_message_key: str,
) -> float | None:
    """Prompt for a required numeric value that must be positive and finite
    (available power, target RPM). Unlike a bare `ask_number` call, which
    only rejects non-numeric text, this also rejects zero/negative/`inf`/
    `nan` -- via `ask_number`'s own `validate` re-prompt loop, so the
    rejection shows an explanatory error dialog rather than silently
    re-showing the same prompt.
    """

    def _validate(value: float) -> ErrorInfo | None:
        if math.isfinite(value) and value > 0:
            return None
        return ErrorInfo(
            code="INVALID_NUMBER",
            message=translate(DEFAULT_LOCALE, invalid_message_key),
            message_key=invalid_message_key,
        )

    return ask_number(
        title=title, label=label, unit=unit, default=default, locale=locale, validate=_validate
    )


def ask_optional_number(
    *, title: str, label: str, unit: str, default: float | None, locale: str
) -> float | None:
    """Prompt for an optional numeric value. Blank keeps ``default``; a
    non-numeric entry is treated as "unknown" (mirrors `console/cli.py`'s
    `_prompt_optional_power`: it warns and falls back to ``default`` rather
    than re-prompting, since this field is never required)."""

    ok_text, cancel_text = _ok_cancel(locale)
    hint = translate(locale, "tui.prompt.power.optional_hint")
    base = (
        translate(locale, "tui.prompt.number.with_default", label=label, unit=unit, default=default)
        if default is not None
        else translate(locale, "tui.prompt.number", label=label, unit=unit)
    )
    text = f"{base}\n{hint}"
    current_default = "" if default is None else str(default)

    raw = input_dialog(
        title=title, text=text, default=current_default, ok_text=ok_text, cancel_text=cancel_text
    ).run()
    if raw is None:
        return default
    raw = raw.strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        message_dialog(
            title=translate(locale, "tui.error.title"),
            text=translate(locale, "tui.prompt.number.invalid"),
            ok_text=ok_text,
        ).run()
        return default


def ask_unit_system(*, default: UnitSystem, locale: str) -> UnitSystem | None:
    options = {
        "metric": translate(locale, "tui.unit_system.metric"),
        "imperial": translate(locale, "tui.unit_system.imperial"),
    }
    choice = ask_choice(
        title=translate(locale, "tui.label.unit_system"),
        label=translate(locale, "tui.label.unit_system"),
        options=options,
        default="metric" if default is UnitSystem.METRIC else "imperial",
        locale=locale,
    )
    if choice is None:
        return None
    return UnitSystem.METRIC if choice == "metric" else UnitSystem.IMPERIAL


def ask_mode(*, default: CalculationMode, locale: str) -> CalculationMode | None:
    options = {mode.value: translate(locale, key) for mode, key in _MODE_OPTION_KEYS.items()}
    choice = ask_choice(
        title=translate(locale, "tui.label.mode"),
        label=translate(locale, "tui.label.mode"),
        options=options,
        default=default.value,
        locale=locale,
    )
    if choice is None:
        return None
    return CalculationMode(choice)


def ask_material_type(*, material_types: list[str], default: str | None, locale: str) -> str | None:
    options = {mt: material_type_label(mt, locale) for mt in material_types}
    return ask_choice(
        title=translate(locale, "tui.label.material_type"),
        label=translate(locale, "tui.label.material_type"),
        options=unique_labels(options),
        default=default,
        locale=locale,
    )


def ask_material(
    *,
    names: list[str],
    config_path: str | None,
    default: str | None,
    locale: str,
    display_locale: str,
) -> str | None:
    materials = {name: get_material(name, config_path) for name in names}
    display = {
        name: display_label(material, display_locale, locale)
        for name, material in materials.items()
        if material is not None
    }
    return ask_choice(
        title=translate(locale, "tui.label.material"),
        label=translate(locale, "tui.label.material"),
        options=unique_labels(display),
        default=default,
        locale=locale,
    )


def ask_tool(
    *,
    names: list[str],
    resolve: Callable[[str, str | None], object | None],
    label_key: str,
    config_path: str | None,
    default: str | None,
    locale: str,
    display_locale: str,
) -> str | None:
    """Generalized tool prompt (drilling tool, end-mill, face-mill) —
    mirrors `console/cli.py`'s `_prompt_mill_tool_choice`/`_prompt_tool_choice`."""

    tools = {name: resolve(name, config_path) for name in names}
    display = {
        name: display_label(tool, display_locale, locale)  # type: ignore[arg-type]
        for name, tool in tools.items()
        if tool is not None
    }
    label = translate(locale, label_key)
    return ask_choice(
        title=label,
        label=label,
        options=unique_labels(display),
        default=default,
        locale=locale,
    )


def ask_drilling_tool(
    *,
    names: list[str],
    config_path: str | None,
    default: str | None,
    locale: str,
    display_locale: str,
) -> str | None:
    return ask_tool(
        names=names,
        resolve=get_tool,
        label_key="tui.label.tool",
        config_path=config_path,
        default=default,
        locale=locale,
        display_locale=display_locale,
    )


_SPINDLE_SPEED_MODE_LABEL_KEYS = {
    CalculationMode.STANDARD: "tui.result.spindle_speed.mode.standard",
    CalculationMode.POWER_CONSTRAINED: "tui.result.spindle_speed.mode.power_constrained",
    CalculationMode.FIXED_RPM: "tui.result.spindle_speed.mode.fixed_rpm",
}


def format_result(result, labels: dict[str, str], locale: str) -> str:
    """Render a `CalculationResult` as display text. Ports `console/cli.py`'s
    `_display_result` (research.md #3), returning a string for a
    `message_dialog` instead of `print()`-ing line by line."""

    if result.error is not None:
        return render_error(result.error, locale)

    mode_label = translate(locale, _SPINDLE_SPEED_MODE_LABEL_KEYS[result.mode])
    mode_suffix = translate(locale, "tui.result.spindle_speed.mode_suffix", label=mode_label)
    lines = [
        translate(
            locale,
            "tui.result.spindle_speed",
            value=f"{result.spindle_speed_rpm:.1f}",
            mode_suffix=mode_suffix,
        ),
        translate(
            locale,
            "tui.result.feed_rate",
            value=f"{result.feed_rate:.1f}",
            unit=labels["feed_rate"],
        ),
        translate(locale, "tui.result.machining_time", value=f"{result.machining_time:.2f}"),
        translate(locale, "tui.result.torque", value=f"{result.torque:.1f}", unit=labels["torque"]),
        translate(
            locale,
            "tui.result.power_required",
            value=f"{result.power_required:.2f}",
            unit=labels["power"],
        ),
    ]
    if result.material_removal_rate is not None:
        lines.append(
            translate(
                locale,
                "tui.result.material_removal_rate",
                value=f"{result.material_removal_rate:.2f}",
                unit=labels["material_removal_rate"],
            )
        )
    text = "\n".join(lines)
    if result.feasibility_warning:
        text += translate(locale, "tui.result.warning", message=result.feasibility_warning)
    return text


def show_result(result, labels: dict[str, str], locale: str) -> None:
    """Display a calculation's result (or error) in a message dialog."""

    is_error = result.error is not None
    title_key = "tui.result.error.title" if is_error else "tui.result.title"
    message_dialog(
        title=translate(locale, title_key),
        text=format_result(result, labels, locale),
        ok_text=translate(locale, "tui.action.ok"),
    ).run()
