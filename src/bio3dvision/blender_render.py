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
import math
import os
import sys

import bpy  # type: ignore[import-not-found]  # provided by Blender, absent in CI

DEPTH_STEM = "depth_left"
IMAGE_STEM = "image"

# Blender's default camera sensor width. focal_px() reads it back off the camera;
# this constant only turns a wanted f_px into the lens length that produces it.
SENSOR_WIDTH_MM = 36.0


def parse_args(argv: list[str]) -> argparse.Namespace:
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Render a rectified stereo pair.")
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--baseline", type=float, default=0.065, help="interocular, metres")
    parser.add_argument("--res", type=int, nargs=2, default=[320, 240], metavar=("W", "H"))
    parser.add_argument("--samples", type=int, default=32)
    parser.add_argument("--lens", type=float, default=None, help="focal length, mm")
    parser.add_argument(
        "--pano",
        action="store_true",
        help="equirectangular capture: both eyes panoramic, full sphere",
    )
    parser.add_argument(
        "--poses",
        default=None,
        metavar="JSON",
        help="explicit eye poses for any scene builder: {'left': {...}, 'right': {...}}",
    )
    parser.add_argument(
        "--sphere-cards",
        type=float,
        nargs="+",
        default=None,
        metavar="Z",
        help="tiled planes in LONGITUDE bands, for the spherical depth falsifier",
    )
    parser.add_argument(
        "--sphere-textured",
        action="store_true",
        help="give the sphere-cards planes a noise texture, so a matcher can run",
    )
    parser.add_argument("--sphere-seed", type=int, default=0, help="texture seed")
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
    parser.add_argument(
        "--markers",
        default=None,
        help="JSON file of world-frame marker positions and eye poses; geometry apparatus",
    )
    parser.add_argument(
        "--scene",
        default=None,
        help="build the scene written by bio3dvision.scene_model.write_scene, from this directory",
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


def make_panoramic(cam_data: object) -> None:
    """Turn a camera into a FULL-SPHERE equirectangular one. **Blender 5.2 API.**

    ``panorama_type`` lives on the camera data directly in 5.2; in older releases
    it sat under ``cam.data.cycles``. Both are set defensively, because a silently
    unset panorama type renders a perspective image that looks like a plausible
    view of the same scene — the failure mode this repository has now recorded
    three times under different names.

    Longitude and latitude are set to the full sphere explicitly rather than left
    at their defaults, so a future default change cannot quietly narrow the field.
    """
    cam_data.type = "PANO"
    if hasattr(cam_data, "panorama_type"):
        cam_data.panorama_type = "EQUIRECTANGULAR"
    elif hasattr(cam_data, "cycles"):  # pragma: no cover - older Blender
        cam_data.cycles.panorama_type = "EQUIRECTANGULAR"
    else:  # pragma: no cover - build-dependent
        raise RuntimeError("this Blender exposes no panorama_type; equirect is unavailable")
    for attr, value in (
        ("longitude_min", -math.pi),
        ("longitude_max", math.pi),
        ("latitude_min", -math.pi / 2.0),
        ("latitude_max", math.pi / 2.0),
    ):
        if hasattr(cam_data, attr):
            setattr(cam_data, attr, value)


def build_sphere_calibration_scene(
    distances: list[float], res: tuple[int, int], textured: bool = False, seed: int = 0
) -> None:
    """Fronto-parallel planes at known distances, each in its own LONGITUDE band.

    The spherical counterpart of :func:`build_calibration_scene`, and it carries
    that function's hard-won constraint: **planes are tiled, not stacked.**
    Concentric shells at increasing distance would leave exactly one distance in
    the depth pass, and a falsifier written to check three would silently check
    one. On a sphere the failure is worse, not better — a full shell occludes
    everything behind it in EVERY direction.

    Each plane faces the camera along its own longitude, so its analytic RANGE at
    a given direction is ``z / (d . n)`` and its analytic PLANAR depth is ``z``.
    A single render therefore checks the distances AND discriminates the two
    conventions, which on a spherical camera is the question that matters: there
    is no image plane, so "planar" is a statement about a normal that has to be
    named rather than assumed.

    Bands are separated by gaps left empty on purpose; those directions have no
    ray hit and load as ``nan``, exercising the non-hit path in the same render.
    """
    _reset_to_camera_only()
    ordered = sorted(distances)
    span = 2.0 * math.pi / len(ordered)
    gap = span * 0.05
    # Half-angle each plane must cover in longitude, and in latitude. Wide enough
    # that most of the sphere carries geometry: an experiment whose premise is a
    # COMPLETE capture should not score a small patch of one.
    half_lon = (span - 2.0 * gap) / 2.0
    half_lat = math.radians(58.0)

    for i, z in enumerate(ordered):
        centre_lon = -math.pi + span * (i + 0.5)
        # LONGITUDE IS MEASURED ABOUT THE CAMERA'S UP AXIS, which for a Blender
        # camera at the identity is world +Y. Tiling about world Z instead puts
        # every plane on a circle THROUGH THE POLES, so they stack in latitude and
        # overlap in longitude — measured on the first run of this function, and it
        # reduced a three-way check to an overlapping mess in exactly the way the
        # pinhole version's docstring warns about for stacked shells.
        nx, nz = math.sin(centre_lon), -math.cos(centre_lon)
        half_w = z * math.tan(half_lon)
        half_h = z * math.tan(half_lat)
        bpy.ops.mesh.primitive_plane_add(size=2.0, location=(z * nx, 0.0, z * nz))
        plane = bpy.context.object
        plane.scale = (half_w, half_h, 1.0)
        # Default plane lies in XY with normal +Z; rotate about Y so the normal
        # points back at the camera along its own longitude.
        plane.rotation_euler = (0.0, -centre_lon, 0.0)
        material = bpy.data.materials.new(f"Card_{i}")
        material.use_nodes = True
        nodes = material.node_tree.nodes
        nodes.clear()
        emission = nodes.new("ShaderNodeEmission")
        emission.inputs["Strength"].default_value = 1.0
        output = nodes.new("ShaderNodeOutputMaterial")
        links = material.node_tree.links
        if textured:
            # HIGH-FREQUENCY EMISSIVE TEXTURE, so a block matcher has something to
            # match. Emission and not diffuse: the depth pass must not depend on
            # lighting, and neither should the intensity a matcher reads.
            noise = nodes.new("ShaderNodeTexNoise")
            noise.inputs["Scale"].default_value = 55.0 + 7.0 * i
            noise.inputs["Detail"].default_value = 8.0
            if "W" in noise.inputs:
                noise.inputs["W"].default_value = float(seed) * 13.0 + i
            coord = nodes.new("ShaderNodeTexCoord")
            links.new(coord.outputs["Object"], noise.inputs["Vector"])
            links.new(noise.outputs["Fac"], emission.inputs["Color"])
        else:
            emission.inputs["Color"].default_value = (0.2 + 0.2 * i, 0.5, 0.8, 1.0)
        links.new(emission.outputs["Emission"], output.inputs["Surface"])
        plane.data.materials.append(material)


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


def build_scene_from_model(scene_dir: str) -> dict:
    """Build the scene described by bio3dvision.scene_model.write_scene.

    Reads ``scene.json`` and ``texture.exr`` and makes one textured plane per
    surface. Every number it needs — world extent, UV window, camera position —
    was computed on the tested side and is read, not recomputed here. That is the
    point of the split: the arithmetic that decides where a surface goes is
    checkable, and this function only places what it is told to.

    Returns the spec, so the caller can take the camera from it.

    THE MATERIAL IS AN EMITTER AND THE TEXTURE IS SAMPLED WITH 'Closest'. Both are
    required for a rendered pixel to equal a texture value: any shading model
    would apply a cosine falloff the fixture does not have, and any interpolation
    would blend neighbouring texels. The image is tagged ``Non-Color`` so Blender
    does not apply an sRGB decode to values that are not colours.
    """
    with open(os.path.join(scene_dir, "scene.json")) as handle:
        spec = json.load(handle)

    _reset_to_camera_only()
    image = bpy.data.images.load(os.path.join(scene_dir, spec["texture"]))
    image.colorspace_settings.name = "Non-Color"

    for i, surface in enumerate(spec["surfaces"]):
        x_min, x_max, y_min, y_max = surface["extent_world"]
        u_min, u_max, v_min, v_max = surface["uv_window"]

        bpy.ops.mesh.primitive_plane_add(size=2.0)
        plane = bpy.context.active_object
        plane.name = f"surface_{i}_{surface['depth_m']:.3f}m"
        plane.location = ((x_min + x_max) / 2.0, (y_min + y_max) / 2.0, -surface["depth_m"])
        plane.scale = ((x_max - x_min) / 2.0, (y_max - y_min) / 2.0, 1.0)
        plane.rotation_euler = (0.0, 0.0, 0.0)

        mesh = plane.data
        if not mesh.uv_layers:
            mesh.uv_layers.new()
        uv = mesh.uv_layers.active.data
        for loop in mesh.loops:
            # Local vertex coords are +/-1 on a size=2 plane, so this maps each
            # corner onto the surface's own window of the shared texture
            # regardless of the order Blender emits the vertices in.
            vx, vy, _ = mesh.vertices[loop.vertex_index].co
            uv[loop.index].uv = (
                u_min + (vx + 1.0) / 2.0 * (u_max - u_min),
                v_min + (vy + 1.0) / 2.0 * (v_max - v_min),
            )

        material = bpy.data.materials.new(f"surface_mat_{i}")
        material.use_nodes = True
        nodes = material.node_tree.nodes
        nodes.clear()
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Linear"
        tex.extension = "EXTEND"
        emission = nodes.new("ShaderNodeEmission")
        emission.inputs["Strength"].default_value = 1.0
        output = nodes.new("ShaderNodeOutputMaterial")
        links = material.node_tree.links
        links.new(tex.outputs["Color"], emission.inputs["Color"])
        links.new(emission.outputs["Emission"], output.inputs["Surface"])
        plane.data.materials.append(material)

    return spec


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


def build_marker_scene(spec: dict) -> None:
    """Emissive point markers on a black world. **Geometry apparatus, not a stimulus.**

    Exists so the gaze-contingent falsifiers can be answered by MEASURING WHERE A
    KNOWN POINT LANDS rather than by looking at a render. A marker at the fixation
    point must image at the principal point in both eyes; markers along the plane
    of regard must image on one row. Neither question is answerable from a
    textured scene, and "it looks right" is exactly the evidence a wrong basis
    change survives.

    ``spec["markers"]`` are WORLD-frame positions, converted outside Blender by
    ``scene_model.WORLD_FROM_HEAD`` — this module cannot import that.
    """
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    for node in world.node_tree.nodes:
        if node.type == "BACKGROUND":
            node.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
            node.inputs["Strength"].default_value = 0.0

    data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    radius = float(spec.get("marker_radius", 0.004))
    for i, position in enumerate(spec["markers"]):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=tuple(position))
        sphere = bpy.context.active_object
        sphere.name = f"marker_{i}"
        _emission_material(sphere, 1.0, 1000 + i)


def place_eyes_from_poses(base_cam: object, poses: dict) -> dict[str, object]:
    """Two cameras whose world matrices are given explicitly. **Gaze-contingent.**

    The matrices come from ``scene_model.eye_camera_poses``, which computes them
    outside Blender because this module may import nothing but the standard
    library and ``bpy``. That constraint is why the basis change — the part most
    likely to be wrong — is testable without a renderer.

    **Blender's native toe-in is not used and must not be.** It is yaw-only and
    zero-torsion, so it is correct only for a symmetric horizontal fixation, which
    is precisely the case that cannot detect a torsion error. Each matrix is set
    whole, torsion included.

    The base camera's own orientation is DISCARDED here rather than composed with:
    the poses are already complete world matrices in the scene's frame, and
    multiplying by whatever the .blend happened to have would silently add a
    rotation nobody asked for.
    """
    from mathutils import Matrix  # type: ignore[import-not-found]  # Blender-only

    cams: dict[str, object] = {}
    for name in ("left", "right"):
        cam = base_cam.copy()
        cam.data = base_cam.data.copy()
        cam.name = f"Cam_{name}"
        bpy.context.scene.collection.objects.link(cam)
        cam.matrix_world = Matrix([list(row) for row in poses[name]["matrix_world"]])
        # The PRINCIPAL-POINT SHIFT. A rectifying orientation has its x-axis along
        # the baseline, which forces its forward axis to azimuth zero, so a
        # rectified camera cannot ROTATE to an eccentric gaze. It can slide its
        # sensor window instead: shift is a translation in the image plane and
        # leaves the pair rectified, because both eyes take the same shift.
        # Absent or zero keeps every earlier render reproducible.
        cam.data.shift_x = float(poses[name].get("shift_x", 0.0))
        cam.data.shift_y = float(poses[name].get("shift_y", 0.0))
        cams[name] = cam
    return cams


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

    # POINT SAMPLING, and it is load-bearing for the scene-model comparison.
    # Cycles jitters sample positions inside each pixel and averages, so with a
    # 'Closest'-sampled texture a pixel near a texel boundary would average two
    # neighbouring texels and the rendered image would be a slightly blurred copy
    # of the texture rather than the texture. A box filter of near-zero width
    # collapses every sample onto the pixel centre.
    if hasattr(scene, "cycles"):
        if hasattr(scene.cycles, "pixel_filter_type"):
            scene.cycles.pixel_filter_type = "BOX"
        if hasattr(scene.cycles, "filter_width"):
            scene.cycles.filter_width = 1e-4

    # No view transform on anything written as data. AgX would tone-map the
    # emission values into something that still looks like an image.
    if hasattr(scene, "view_settings"):
        try:
            scene.view_settings.view_transform = "Standard"
        except TypeError:  # pragma: no cover - build-dependent enum
            print("[render] WARNING: could not set view_transform=Standard", file=sys.stderr)

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


def setup_outputs(scene: object, out_dir: str) -> tuple[object, object, object]:
    """File Output nodes for the Z pass and for the beauty pass, both float EXR.

    Returns ``(tree, depth_node, image_node)``. The depth node is muted for the
    right eye by the caller: a single depth pass is all the loop consumes.

    **Colour management must not touch either.** With ``save_as_render`` on,
    Blender applies the scene view transform on write, which would turn metres
    into tone-mapped nonsense that still looks like a plausible depth map — and
    would do the same to an emission value that is supposed to equal a texture
    value.

    THE BEAUTY PASS GOES OUT AS FLOAT EXR AS WELL AS PNG, and the EXR is the one
    the loader reads. 8-bit PNG cannot carry the claim this scene model rests on:
    it quantises to 256 levels and, through the display transform, is sRGB-encoded
    rather than linear. Either alone is enough to stop a rendered pixel equalling
    a texture value. The PNG is kept because it is what a person opens to look at
    the render.
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

    depth_node = _exr_output(tree, render_layers, out_dir, DEPTH_STEM, "Depth")
    image_node = _exr_output(tree, render_layers, out_dir, IMAGE_STEM, "Image")

    if api >= 5:
        # 5.0 removed the Composite node; a Group Output terminates the tree now.
        group_out = tree.nodes.new("NodeGroupOutput")
        tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        tree.links.new(group_out.inputs["Image"], render_layers.outputs["Image"])

    return tree, depth_node, image_node


def _exr_output(
    tree: object, render_layers: object, out_dir: str, stem: str, socket: str
) -> object:
    """One File Output node writing ``socket`` to 32-bit float EXR, raw."""
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
            node.file_output_items.new("FLOAT", stem)
        else:
            node.file_output_items[0].name = stem
    else:  # Blender <= 4.x
        node.base_path = out_dir
        node.file_slots[0].path = f"{stem}_"

    try:
        node.format.file_format = "OPEN_EXR"
        node.format.color_depth = "32"
        node.format.color_mode = "BW"
    except TypeError as exc:
        raise RuntimeError(
            f"could not set the {stem!r} output format: {exc}. The File Output "
            "node is probably still in multi-layer mode."
        ) from exc

    if hasattr(node, "save_as_render"):
        node.save_as_render = False
    if hasattr(node.format, "color_management"):
        node.format.color_management = "OVERRIDE"

    tree.links.new(render_layers.outputs[socket], node.inputs[0])
    return node


def _settle_filename(out_dir: str, stem: str, target_name: str) -> None:
    """Rename Blender's decorated File Output result to ``target_name``.

    The written name is the node's ``file_name`` concatenated with the output
    item's name, and older versions appended a frame number too. Globbing rather
    than reconstructing it is deliberate: the reconstruction is what breaks on an
    API change, and it breaks by silently leaving the file under a name the
    loader does not look for.
    """
    target = os.path.join(out_dir, target_name)
    written = sorted(glob.glob(os.path.join(out_dir, f"{stem}*.exr")))
    written = [w for w in written if os.path.basename(w) != target_name]
    if not written:
        if os.path.exists(target):
            return
        raise RuntimeError(
            f"the {stem!r} pass wrote no EXR into {out_dir}. Files present: "
            f"{sorted(os.listdir(out_dir))}"
        )
    os.replace(written[0], target)


def render_stereo(
    out: str,
    baseline: float = 0.065,
    res: tuple[int, int] = (320, 240),
    samples: int = 32,
    lens: float | None = None,
    eye_poses: dict | None = None,
    panoramic: bool = False,
) -> dict[str, object]:
    """Render the pair and the left depth pass, and write the contract.

    ``eye_poses`` makes the render **gaze-contingent**: each camera's world matrix
    is set from the oculomotor geometry rather than copied from the base camera.
    ``None`` keeps the rectified-parallel path exactly as it was, which is what
    lets every render made before this step still be reproduced.
    """
    out = os.path.abspath(out)
    os.makedirs(out, exist_ok=True)

    scene = bpy.context.scene
    base = ensure_camera()
    if lens is not None:
        base.data.lens = lens

    configure_render(scene, res, samples)
    cams = (
        make_stereo_cameras(base, baseline)
        if eye_poses is None
        else place_eyes_from_poses(base, eye_poses)
    )
    if panoramic:
        # AFTER the cameras are made: both are copies of `base`, and each copy
        # carries its own camera data, so the projection must be set on each.
        for cam in cams.values():
            make_panoramic(cam.data)
    _, depth_node, _image_node = setup_outputs(scene, out)

    for name in ("left", "right"):
        scene.camera = cams[name]
        scene.render.filepath = os.path.join(out, f"{name}.png")
        depth_node.mute = name != "left"
        bpy.ops.render.render(write_still=True)
        # Settle immediately: both eyes write under the same stem, so the second
        # render would otherwise overwrite or sit beside the first ambiguously.
        _settle_filename(out, IMAGE_STEM, f"{name}.exr")
        if name == "left":
            _settle_filename(out, DEPTH_STEM, f"{DEPTH_STEM}.exr")

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
        "geometry": ("rectified_parallel" if eye_poses is None else "gaze_contingent"),
        "projection": ("equirectangular" if panoramic else "pinhole"),
        "depth_pass": "Z",
        # Not inferred here. infer_depth_convention() answers it, and only on a
        # fronto-parallel calibration render; establish it per Blender version.
        "depth_is_radial": None,
    }
    with open(os.path.join(out, "params.json"), "w") as handle:
        json.dump(params, handle, indent=2)

    print(f"[render] {out}: left/right .png and .exr, {DEPTH_STEM}.exr, params.json")
    print(f"[render] f_px={params['f_px']:.3f} baseline={baseline} on {params['blender_version']}")
    return params


def main() -> None:
    args = parse_args(sys.argv)
    res = (int(args.res[0]), int(args.res[1]))
    chosen = [
        n
        for n, v in (
            ("--cards", args.cards),
            ("--sphere-cards", args.sphere_cards),
            ("--wall", args.wall),
            ("--scene", args.scene),
        )
        if v is not None and v != []
    ]
    if len(chosen) > 1:
        raise SystemExit(f"{', '.join(chosen)} build different scenes; pass one")

    baseline, lens = args.baseline, args.lens
    eye_poses = None
    if args.markers:
        with open(args.markers) as handle:
            spec = json.load(handle)
        build_marker_scene(spec)
        eye_poses = spec["eye_poses"]
        res = (int(spec["W"]), int(spec["H"]))
        baseline = float(spec["baseline"])
        lens = float(spec["f_px"]) * SENSOR_WIDTH_MM / res[0]
    elif args.scene:
        spec = build_scene_from_model(args.scene)
        eye_poses = spec.get("eye_poses")
        params = spec["params"]
        res = (int(params["W"]), int(params["H"]))
        baseline = float(params["baseline"])
        # The camera is derived from the model, not passed in: f_px is a property
        # of the scene being reproduced, and letting a CLI flag override it is how
        # the two scenes would silently stop being the same scene.
        lens = float(params["f_px"]) * SENSOR_WIDTH_MM / res[0]
    elif args.sphere_cards:
        build_sphere_calibration_scene(
            list(args.sphere_cards), res, textured=args.sphere_textured, seed=args.sphere_seed
        )
    elif args.cards:
        build_calibration_scene(list(args.cards), res)

    if args.poses:
        # Applies to ANY scene builder, unlike --markers and --scene which each
        # carry their own. Needed to render one scene from two orientations, which
        # is how fc-013's claim is checked rather than asserted.
        with open(args.poses) as handle:
            eye_poses = json.load(handle)
    elif args.wall is not None:
        build_wall_scene(float(args.wall), res)

    render_stereo(args.out, baseline, res, args.samples, lens, eye_poses, panoramic=args.pano)


if __name__ == "__main__":
    main()
