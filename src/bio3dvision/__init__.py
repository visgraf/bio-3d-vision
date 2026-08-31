"""bio-3d-vision — a research project on active 3D vision.

Contains one thing: a **faithful port** of the predecessor's active-stereo loop
(``visgraf/bioeye@e908170``), its analytic fixture, and its four-panel figure.
It is a measured baseline, not the intended architecture — see ``loop.py`` for
the three defects carried over deliberately, and ``docs/state.yaml`` for what
runs.

**Flat by decision, not by accident.** No per-layer subpackages. The predecessor
split its library into one directory per framework layer and the directories
filled unevenly — measured at ``visgraf/active-stereo@3f7a263``, stimulus
infrastructure reached 42.1% of the library (2069 of 4913 lines) while scaling,
control and policy together came to 9.1% (446 lines). Structure is added when
something needs it. Recorded as ``fc-002`` in ``docs/state.yaml``.
"""

from bio3dvision.baseline import BaselineRun, error_summary, run_baseline
from bio3dvision.belief import HEAD_FRAME, HeadFrameBelief
from bio3dvision.blender_load import (
    infer_depth_convention,
    load_render,
    radial_to_planar,
    read_exr_depth,
    read_exr_image,
    render_provenance,
)
from bio3dvision.figure import PanelArrays, panel_arrays, save_result_fig
from bio3dvision.fixture import CameraParams, make_synthetic_scene, true_disparity
from bio3dvision.loop import ActiveStereo, scale_to_depth
from bio3dvision.matching import (
    cost_volume,
    decode_disparity,
    front_end_block,
    lr_consistency,
)
from bio3dvision.oculomotor import (
    Estimate,
    EyeRotations,
    Fixation,
    FixationProposal,
    RefusalReason,
    StereoRig,
    TargetRefused,
    eye_rotations,
    fixation_distance,
    fixation_point,
    is_forward_gaze,
    rectification_rotation,
    require_forward_azimuth,
    target_to_fixation,
)
from bio3dvision.sampling import (
    RECTIFIED_LEFT_CAMERA,
    PinholeSampling,
    SamplingModel,
    route_through_sampling,
)

__all__ = [
    "ActiveStereo",
    "BaselineRun",
    "CameraParams",
    "Estimate",
    "EyeRotations",
    "Fixation",
    "FixationProposal",
    "HEAD_FRAME",
    "HeadFrameBelief",
    "PanelArrays",
    "PinholeSampling",
    "RECTIFIED_LEFT_CAMERA",
    "RefusalReason",
    "SamplingModel",
    "StereoRig",
    "TargetRefused",
    "cost_volume",
    "decode_disparity",
    "error_summary",
    "eye_rotations",
    "fixation_distance",
    "fixation_point",
    "front_end_block",
    "infer_depth_convention",
    "is_forward_gaze",
    "load_render",
    "lr_consistency",
    "make_synthetic_scene",
    "panel_arrays",
    "radial_to_planar",
    "read_exr_depth",
    "read_exr_image",
    "rectification_rotation",
    "render_provenance",
    "require_forward_azimuth",
    "route_as_direction",
    "route_through_sampling",
    "run_baseline",
    "save_result_fig",
    "scale_to_depth",
    "target_to_fixation",
    "true_disparity",
]

__version__ = "0.0.0"
