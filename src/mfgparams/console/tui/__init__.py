"""Full-screen text GUI for ``mfgparams.console`` (specs/017-console-text-gui).

Replaces the line-based REPL as the sole interactive entry point. Built on
prompt-toolkit (confirmed by that feature's technical spike). Contains no
calculation logic of its own -- every result comes from the public
``mfgparams`` calculation API, exactly as the REPL it replaces did.
"""

from __future__ import annotations
