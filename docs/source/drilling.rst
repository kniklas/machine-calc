Drilling calculations (user guide)
===================================

mfgparams calculates parameters for twist-drill **drilling**, alongside
milling (end milling and face milling). This page covers using it from the
interactive text GUI; see :doc:`drilling-api` for the library API.

Selecting an operation in the text GUI
---------------------------------------

Launch the text GUI with::

    mfgparams

(equivalently, ``python -m mfgparams`` or ``python -m mfgparams.console`` —
all three reach the same interface.) The top-level menu offers **Machining**,
**Configuration**, **About**, and **Help**; each item is reachable with the
arrow keys and Enter, or its underlined keyboard shortcut. Choosing
**Machining** opens a submenu of **Milling** and **Drilling** — selecting
**Drilling** walks through a sequence of screens for unit system,
calculation mode, material type, material, drilling tool, drill diameter,
hole depth, and available power, in that order, before showing the result.
Choosing **Milling** instead switches to the flow described in
:doc:`milling`.

After a result is shown, dismissing it returns to the top-level menu, so you
can start another calculation — the same operation or a different one —
without leaving the text GUI. Each operation remembers its *own* previous
answers as defaults for the rest of the session, so switching from drilling
to milling and back does not lose your drilling inputs.

Drilling inputs
----------------

After the unit system, calculation mode, material type, material and tool,
drilling asks for two geometry values:

===========================  =========================================================
Prompt                       Meaning
===========================  =========================================================
Drill diameter                Diameter of the twist drill, in mm / in.
Hole depth                    Depth of the hole to be drilled, in mm / in.
===========================  =========================================================

Calculation modes
-----------------

Right after choosing the unit system, the text GUI asks for a calculation
mode: ``standard``, ``power-constrained``, or ``fixed-rpm``.

``standard``
    The unconstrained calculation used throughout the rest of this guide.
    Available power stays optional and only advisory: if the calculated
    power exceeds it, the result is shown anyway with a warning.

``power-constrained``
    Available power becomes a **required** screen instead of an optional
    one, and the result label always reads "adjusted to fit available
    power" instead of "recommended" — regardless of whether an adjustment
    actually happened. If your machine can already deliver the calculated
    power the numeric values are unchanged even though the label switches.
    Otherwise the spindle speed is reduced until the power required
    matches what you supplied exactly. A budget too small for any feasible
    spindle speed is **not** re-prompted at this step — the calculation
    itself fails with an "infeasible power budget" error, which is
    displayed in place of a result, and dismissing it returns to the
    top-level menu rather than asking for available power again.

``fixed-rpm``
    Adds a required "Target spindle speed (RPM)" screen. The spindle speed
    in the result is exactly what you entered — labeled "user-specified" —
    and every other value is recomputed for that speed. Available power
    stays optional/advisory here too, so an insufficient machine still
    produces a result, with a warning.

Starting another Drilling calculation from the menu lets you pick a
different mode; any previous mode's power/RPM answer is cleared rather than
carried over as a stale default.

Reading the results
--------------------

A drilling result looks like this (10 mm diameter, 25 mm depth, Mild Steel,
Carbide, standard mode)::

    Spindle speed:     1989.4 RPM   (recommended)
    Feed rate:         437.7 mm/min
    Machining time:    0.06 min
    Torque:            10.5 N·m
    Power required:    2.18 kW

These five lines mean the same as they do for milling: spindle speed and
feed rate describe how the drill is driven, machining time is how long the
hole takes to cut, and torque/power are what the spindle needs to deliver.
Drilling does not report a material removal rate — that line is specific to
milling and never appears in a drilling result.

If you supply an available machine power and the calculated power exceeds
it, the result is still shown, with a warning line telling you the cut is
beyond what the machine can deliver.

Limits and validation
----------------------

The drill diameter and hole depth are validated before anything is
calculated, and an invalid value at either prompt is re-prompted rather
than aborting the session (unlike available power or a power-constrained
budget — see "Calculation modes" and "Reading the results" above, where an
invalid/infeasible value instead produces a warning or an error result).
The interactive CLI always validates diameter and depth against these
fixed bounds:

===============================  ==========  =========================================
Setting                          Default     Applies to
===============================  ==========  =========================================
``max_diameter_mm``              100.0 mm    Drill diameter.
``max_depth_mm``                 500.0 mm    Hole depth.
===============================  ==========  =========================================

In addition, both values must be positive, finite, and within the bound
above. ``NaN``, ``+inf``/``-inf`` and non-numeric values are all rejected
as ``INVALID_DIAMETER``/``INVALID_DEPTH`` before the bound is checked, so
the CLI re-prompts for them — including the literal ``nan`` that
``float()`` happily parses as ``nan`` — rather than
letting a ``NaN`` poison the calculation (fixed in issue #56).

Library callers
can override these bounds via ``calculate()``'s ``config_path`` argument
(see :doc:`drilling-api`); the CLI does not expose an equivalent flag — its
only configuration flag, ``--materials-config``, overrides materials/tools,
not these geometry bounds.

Assumptions
-----------

The drilling model uses standard twist-drill machining formulas as
published in widely-referenced industry sources (Sandvik Coromant's
"Machining Formulas" reference and Machinery's Handbook), including a
point-engagement allowance approximated as a fraction of drill diameter to
account for the drill point's cutting geometry when computing machining
time. See ``specs/001-metal-drilling-calc/research.md`` for the formulas
and their sources.
