"""bio-3d-vision — a research project on active 3D vision.

Empty on purpose. There is no geometry, no matcher, no stimulus and no loop here
yet; see ``docs/state.yaml`` for what actually runs.

**Flat by decision, not by accident.** This package has no per-layer
subpackages. The predecessor split its library into one directory per framework
layer and the directories filled unevenly — measured at
``visgraf/active-stereo@3f7a263``, stimulus infrastructure reached 42.1% of the
library (2069 of 4913 lines) while scaling, control and policy together — the
three layers that make it *active* and *Bayesian* rather than a stereo matcher —
came to 9.1% (446 lines). A directory per layer is an invitation to fill it.

Structure is added when something needs it. Recorded as ``fc-002`` in
``docs/state.yaml``.
"""

__all__: list[str] = []

__version__ = "0.0.0"
