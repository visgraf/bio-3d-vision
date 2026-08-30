"""Render a rectified stereo pair with depth ground truth. **Nothing here is tested.**

This module runs inside **Blender's** bundled Python, not the project
environment. It imports ``bpy``, which does not exist in CI, so no test in this
repository executes a line of it and none can. ``gap-009`` records that the same
was true of the entire Blender surface in the reference; the difference here is
only that the line is drawn and stated. Everything downstream of what this writes
lives in :mod:`bio3dvision.blender_load`, which is tested.

Keep that boundary. Work moved into this file leaves the reach of the suite, so
this file does the least it can: it configures Blender and writes Blender's own
formats. It performs no unit conversion, no depth-convention correction and no
normalisation — those are in the loader, under test.

Dependencies are the standard library and ``bpy`` alone. Blender ships numpy, but
importing it here would invite exactly the drift this boundary exists to prevent.

Usage
-----
    blender --background scene.blend \\
        --python src/bio3dvision/blender_render.py -- \\
        --out data/scenes/office --baseline 0.065 --res 320 240

    # with no .blend, the two ground-truth scenes this module can build itself:
    blender --background --python src/bio3dvision/blender_render.py -- \\
        --out data/scenes/cards --cards 2.0 3.0 4.5   # tiled planes, for depth
    blender --background --python src/bio3dvision/blender_render.py -- \\
        --out data/scenes/wall  --wall 3.0            # flat wall, for the convention

Blender takes a script PATH, not a module name; ``--python -m`` is not a thing.

Note the bare ``--``: everything after it reaches this script rather than Blender.

Output contract, in ``--out``
-----------------------------
    left.png  right.png     the pair, 8-bit grayscale
    depth_left.exr          left-eye Z pass, 32-bit float, metres
    params.json             f_px, baseline, H, W, plus renderer provenance

This is bioeye's contract at ``e908170``, kept deliberately: that repository
ships a real render in it, which is what lets the loader be tested against
genuine renderer output with no Blender present.

Geometry is **rectified parallel** — two cameras with identical orientation,
offset along the base camera's local X. Not toe-in, and not off-axis. The loop
solves a pure 1-D horizontal search and wants ``d = f_px * baseline / Z`` to hold
exactly; the convergence modes the reference supports are out of scope here and
would each need a decision of their own.

Blender version handling follows the reference: 5.0 removed ``Scene.node_tree``,
replaced ``base_path``/``file_slots`` with ``directory``/``file_name``, and put
the File Output mode behind ``node.format.media_type``. Both API shapes are
branched on rather than assumed.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import bpy  # type: ignore[import-not-found]  # provided by Blender, absent in CI

DEPTH_STEM = "depth_left"


def parse_args(argv: list[str]) -> argparse.Namespace:
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Render a rectified stereo pair.")
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--baseline", type=float, default=0.065, help="interocular, metres")
    parser.add_argument("--res", type=int, nargs=2, default=[320, 240], metavar=("W", "H"))
    parser.add_argument("--samples", type=int, default=32)
    parser.add_argument("--lens", type=float, default=None, help="focal length, mm")
    parser.add_argument(
        "--cards",
        type=float,
        nargs="*",
        default=None,
        help=(
            "build fronto-parallel planes at these distances in metres, tiled "
            "across the frame, instead of using the loaded .blend"
        ),
    )
    parser.add_argument(
        "--wall",
        type=float,
        default=None,
        help="build a single flat wall at this distance: the convention calibration render",
    )
    return parser.parse_args(argv)


def ensure_camera() -> object:
    """The scene's camera, creating one looking down -Z if there is none."""
    cam = bpy.context.scene.camera
    if cam is None:
        data = bpy.data.cameras.new("Cam")
        cam = bpy.data.objects.new("Cam", data)
        bpy.context.scene.collection.objects.link(cam)
        cam.location = (0.0, 0.0, 0.0)
        cam.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.scene.camera = cam
    return cam


def focal_px(cam: object, res_x: int) -> float:
    """Horizontal focal length in pixels, from the Blender camera.

    ``f_px = lens_mm * res_x / sensor_width_mm`` when the sensor fit is
    horizontal, which is Blender's default for landscape renders. The vertical
    fit is handled explicitly rather than left to produce a silently wrong
    number, because everything downstream — disparity, and therefore every depth
    the loop reports — scales linearly with this one value.
    """
    data = cam.data
    if data.sensor_fit == "VERTICAL":
        return float(res_x * data.lens / data.sensor_height)
    return float(res_x * data.lens / data.sensor_width)


def build_calibration_scene(distances: list[float], res: tuple[int, int]) -> None:
    """Fronto-parallel planes at known distances, each in its own vertical band.

    The depth falsifier needs surfaces whose true ``Z`` is known by construction,
    so the loaded depth can be checked against arithmetic rather than against
    another render.

    **They are tiled across the frame rather than stacked behind each other**, and
    that is not cosmetic. Concentric full-frame planes at increasing distance are
    the obvious construction and produce a depth map containing exactly ONE
    distance: the nearest plane occludes the rest, the render succeeds, and a
    falsifier written to check three distances silently checks one. Measured, on
    the first run of this function. Each plane is therefore sized and placed so
    its projection lands inside its own band of image columns, with a gap between
    bands, and the whole set is visible simultaneously.

    The gaps are left empty on purpose. Those pixels have no ray hit and load as
    ``nan``, which exercises the non-hit path in the same render.

    Emission shaders, so the depth pass does not depend on lighting. This scene is
    ground-truth apparatus and not a stimulus; nothing about how it looks should
    be read as one.
    """
    width_px, height_px = res
    cam = _reset_to_camera_only()
    f_px = focal_px(cam, width_px)

    ordered = sorted(distances)
    band = width_px / len(ordered)
    gap_px = max(4.0, band * 0.08)

    for i, z in enumerate(ordered):
        # Image columns this plane must cover, as offsets from the principal
        # point, then back-projected to world units at its own distance.
        c0 = (i * band + gap_px) - (width_px - 1) / 2.0
        c1 = ((i + 1) * band - gap_px) - (width_px - 1) / 2.0
        half_w = (c1 - c0) / 2.0 * z / f_px
        centre_x = (c0 + c1) / 2.0 * z / f_px
        half_h = (height_px / 2.0) * z / f_px * 1.1  # over-fill vertically

        bpy.ops.mesh.primitive_plane_add(size=2.0, location=(centre_x, 0.0, -z))
        plane = bpy.context.active_object
        plane.name = f"card_{i}_{z:.3f}m"
        plane.rotation_euler = (0.0, 0.0, 0.0)
        plane.scale = (half_w, half_h, 1.0)
        # A default plane lies in XY, facing +Z, which is already facing the
        # camera at the origin looking down -Z. No rotation is wanted.
        _emission_material(plane, 0.2 + 0.6 * (i + 1) / (len(ordered) + 1), i)


def build_wall_scene(distance: float, res: tuple[int, int]) -> None:
    """A single flat wall filling the frame — the depth-convention calibration render.

    :func:`~bio3dvision.blender_load.infer_depth_convention` is only meaningful on
    this and refuses to answer on anything else, which is the guard that makes it
    worth carrying. It therefore needs its own scene: the tiled scene above has
    three depths in it and the inference correctly declines to diagnose it.
    """
    width_px, height_px = res
    cam = _reset_to_camera_only()
    f_px = focal_px(cam, width_px)
    half_w = (width_px / 2.0) * distance / f_px * 1.2
    half_h = (height_px / 2.0) * distance / f_px * 1.2

    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, -distance))
    plane = bpy.context.active_object
    plane.name = f"wall_{distance:.3f}m"
    plane.rotation_euler = (0.0, 0.0, 0.0)
    plane.scale = (half_w, half_h, 1.0)
    _emission_material(plane, 0.6, 0)


def _reset_to_camera_only() -> object:
    """Empty the scene and install a camera at the origin looking down -Z."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (0.0, 0.0, 0.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.scene.camera = cam
    return cam


def _emission_material(plane: object, level: float, index: int) -> None:
    """A flat emitter. The grey level separates planes by eye and means nothing else."""
    material = bpy.data.materials.new(f"mat_{index}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (level, level, level, 1.0)
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    plane.data.materials.append(material)


def make_stereo_cameras(base_cam: object, baseline: float) -> dict[str, object]:
    """Two copies of ``base_cam``, offset along its local X by ``+/- baseline/2``.

    Orientations are copied unchanged, which is what makes the pair rectified:
    the epipolar lines are image rows, disparity is horizontal, and
    ``d = f_px * baseline / Z`` holds without rectification.
    """
    from mathutils import Vector  # type: ignore[import-not-found]  # Blender-only

    xaxis = base_cam.matrix_world.to_3x3() @ Vector((1.0, 0.0, 0.0))
    xaxis.normalize()
    cams: dict[str, object] = {}
    for name, sign in (("left", -1.0), ("right", +1.0)):
        cam = base_cam.copy()
        cam.data = base_cam.data.copy()
        cam.name = f"Cam_{name}"
        cam.location = base_cam.location + xaxis * (sign * baseline / 2.0)
        cam.rotation_euler = base_cam.rotation_euler
        bpy.context.scene.collection.objects.link(cam)
        cams[name] = cam
    return cams


def configure_render(scene: object, res: tuple[int, int], samples: int) -> None:
    """Resolution, engine, Z pass, compositing on, denoising off.

    The Z pass must be enabled **before** the compositor tree is built, or the
    Render Layers node exposes no Depth socket to link.

    Denoising stays off. It smooths the beauty pass, which would supply spatial
    structure that a matcher is then credited with having found — the denoiser
    doing the matching's work on exactly the low-texture regions where matching
    is hard.
    """
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "BW"
    scene.render.use_compositing = True

    try:
        scene.render.engine = "CYCLES"
        if hasattr(scene, "cycles"):
            scene.cycles.samples = samples
    except (TypeError, AttributeError):  # pragma: no cover - build-dependent
        print("[render] CYCLES unavailable; using the scene's engine", file=sys.stderr)

    for view_layer in scene.view_layers:
        view_layer.use_pass_z = True

    for owner in (getattr(scene, "cycles", None), *scene.view_layers):
        if owner is not None and hasattr(owner, "use_denoising"):
            owner.use_denoising = False

    scene.frame_set(1)


def compositor_tree(scene: object) -> tuple[object, int]:
    """The scene's compositing tree, across the 4.x/5.x split. Returns ``(tree, api)``.

    Blender 5.0 removed ``Scene.node_tree``: the compositing tree became its own
    datablock, assigned through ``Scene.compositing_node_group``.
    ``Scene.use_nodes`` is deprecated in 5.x and is only touched on the legacy
    path.
    """
    if hasattr(scene, "compositing_node_group"):  # Blender 5.0+
        tree = bpy.data.node_groups.new("bio3dvision_comp", "CompositorNodeTree")
        scene.compositing_node_group = tree
        return tree, 5
    scene.use_nodes = True  # Blender <= 4.x
    return scene.node_tree, 4


def set_individual_files(node: object) -> bool:
    """Switch a File Output node out of multi-layer mode. Returns whether it worked.

    In Blender 5.x the mode lives on ``node.format.media_type`` and **defaults to
    ``MULTI_LAYER_IMAGE``**, which restricts ``file_format`` to exactly
    ``OPEN_EXR_MULTILAYER``. Every other format assignment raises until this is
    set. It must therefore precede any format assignment, not follow it.

    Separate files are also what the loader wants: it reads one pass per file and
    does not walk EXR parts.
    """
    fmt = getattr(node, "format", None)
    if fmt is not None and hasattr(fmt, "media_type"):
        fmt.media_type = "IMAGE"
        return True
    return not hasattr(node, "directory")  # 4.x has no such mode to leave


def setup_depth_output(scene: object, out_dir: str) -> tuple[object, object]:
    """A File Output node writing the left Z pass to 32-bit EXR in metres.

    Returns ``(tree, node)``; the node is muted for the right eye by the caller,
    because a single depth pass is all the loop consumes and rendering the second
    one would be machinery for a question this iteration does not ask.

    **Colour management must not touch the depth pass.** With ``save_as_render``
    on, Blender applies the scene view transform on write, which would turn
    metres into tone-mapped nonsense that still looks like a plausible depth map.
    """
    tree, api = compositor_tree(scene)
    for node in list(tree.nodes):
        tree.nodes.remove(node)

    render_layers = tree.nodes.new("CompositorNodeRLayers")
    if "Depth" not in render_layers.outputs:
        raise RuntimeError(
            "Render Layers exposes no Depth socket. The Z pass must be enabled "
            "(view_layer.use_pass_z) before the compositor tree is built. "
            f"Sockets present: {[o.name for o in render_layers.outputs]}"
        )

    node = tree.nodes.new("CompositorNodeOutputFile")

    # Must precede everything else on the 5.x path: in multi-layer mode the
    # format enum has exactly one legal value and no output item can be added.
    if not set_individual_files(node):
        print(
            "[render] WARNING: could not leave multi-layer mode; the format "
            "assignment below will probably fail.",
            file=sys.stderr,
        )

    if hasattr(node, "directory"):  # Blender 5.0+
        node.directory = out_dir
        # The written name is `file_name` concatenated with the ITEM's name, so
        # one of the two must be empty or the file is called depth_leftdepth_left.
        node.file_name = ""
        # 5.x starts with NO output items and a single unnamed extend socket.
        # Linking to that socket does not create an item -- measured: the render
        # then completes, reports success, and writes no depth at all. The item
        # has to be added explicitly.
        if not len(node.file_output_items):
            node.file_output_items.new("FLOAT", DEPTH_STEM)
        else:
            node.file_output_items[0].name = DEPTH_STEM
    else:  # Blender <= 4.x
        node.base_path = out_dir
        node.file_slots[0].path = f"{DEPTH_STEM}_"

    try:
        node.format.file_format = "OPEN_EXR"
        node.format.color_depth = "32"
        node.format.color_mode = "BW"
    except TypeError as exc:
        raise RuntimeError(
            f"could not set the depth output format: {exc}. The File Output node "
            "is probably still in multi-layer mode."
        ) from exc

    if hasattr(node, "save_as_render"):
        node.save_as_render = False
    if hasattr(node.format, "color_management"):
        node.format.color_management = "OVERRIDE"

    tree.links.new(render_layers.outputs["Depth"], node.inputs[0])

    if api >= 5:
        # 5.0 removed the Composite node; a Group Output terminates the tree now.
        group_out = tree.nodes.new("NodeGroupOutput")
        tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        tree.links.new(group_out.inputs["Image"], render_layers.outputs["Image"])

    return tree, node


def _settle_depth_filename(out_dir: str) -> None:
    """Rename Blender's frame-numbered depth output to ``depth_left.exr``.

    The File Output node appends a frame number, and where it appends it has
    moved between versions. Globbing rather than reconstructing the name is
    deliberate: the reconstruction is what breaks on an API change, and it breaks
    by silently leaving the file under a name the loader does not look for.
    """
    target = os.path.join(out_dir, f"{DEPTH_STEM}.exr")
    if os.path.exists(target):
        return
    written = sorted(glob.glob(os.path.join(out_dir, f"{DEPTH_STEM}*.exr")))
    if not written:
        raise RuntimeError(
            f"the depth pass wrote no EXR into {out_dir}. Files present: "
            f"{sorted(os.listdir(out_dir))}"
        )
    os.replace(written[0], target)


def render_stereo(
    out: str,
    baseline: float = 0.065,
    res: tuple[int, int] = (320, 240),
    samples: int = 32,
    lens: float | None = None,
) -> dict[str, object]:
    """Render the pair and the left depth pass, and write the contract."""
    out = os.path.abspath(out)
    os.makedirs(out, exist_ok=True)

    scene = bpy.context.scene
    base = ensure_camera()
    if lens is not None:
        base.data.lens = lens

    configure_render(scene, res, samples)
    cams = make_stereo_cameras(base, baseline)
    _, depth_node = setup_depth_output(scene, out)

    for name in ("left", "right"):
        scene.camera = cams[name]
        scene.render.filepath = os.path.join(out, f"{name}.png")
        depth_node.mute = name != "left"
        bpy.ops.render.render(write_still=True)

    _settle_depth_filename(out)

    params: dict[str, object] = {
        "f_px": focal_px(base, res[0]),
        "baseline": float(baseline),
        "W": int(res[0]),
        "H": int(res[1]),
        # Provenance. A depth map without the renderer that produced it is prose,
        # for the same reason a measurement without its commit is.
        "blender_version": bpy.app.version_string,
        "blender_build_hash": (
            bpy.app.build_hash.decode()
            if isinstance(bpy.app.build_hash, bytes)
            else str(bpy.app.build_hash)
        ),
        "engine": scene.render.engine,
        "samples": samples,
        "denoising": False,
        "geometry": "rectified_parallel",
        "depth_pass": "Z",
        # Not inferred here. infer_depth_convention() answers it, and only on a
        # fronto-parallel calibration render; establish it per Blender version.
        "depth_is_radial": None,
    }
    with open(os.path.join(out, "params.json"), "w") as handle:
        json.dump(params, handle, indent=2)

    print(f"[render] {out}: left.png right.png {DEPTH_STEM}.exr params.json")
    print(f"[render] f_px={params['f_px']:.3f} baseline={baseline} on {params['blender_version']}")
    return params


def main() -> None:
    args = parse_args(sys.argv)
    res = (int(args.res[0]), int(args.res[1]))
    if args.cards and args.wall is not None:
        raise SystemExit("--cards and --wall build different scenes; pass one")
    if args.cards:
        build_calibration_scene(list(args.cards), res)
    elif args.wall is not None:
        build_wall_scene(float(args.wall), res)
    render_stereo(args.out, args.baseline, res, args.samples, args.lens)


if __name__ == "__main__":
    main()
