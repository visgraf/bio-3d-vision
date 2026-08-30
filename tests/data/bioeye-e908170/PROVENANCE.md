# `bioeye@e908170/data` — a rendered fixture, carried verbatim

Copied byte-for-byte from `visgraf/bioeye` at `e908170`, path `data/`. Real
Blender output, committed to that repository and immutable there.

## What it is for

It is the only thing in this repository that lets the render **loader** be
tested against genuine renderer output with no Blender binary present. `gap-009`
records that nothing inside Blender is covered by any test in the reference;
this fixture does not close that gap — nothing can, from outside Blender — but
it moves the loader out of it.

## What it is NOT for

**It is not a stimulus.** No experiment may draw a result from it. It is a
fixture for the reader, in the same sense that `fc-004` reserves the analytic
fixture for tests: a finding that rested on it would have misused it. It is
four files and it stays four files.

## What it is a fixture OF

Blender 4.x. `render_stereo_blender.py:18` in that repository documents the
script as targeting Blender 3.x/4.x, so this is a **Blender-4 artifact** and
that is exactly why it is worth keeping: the renderer migrated here targets
Blender 5, and holding a 4.x artifact fixed is what makes version drift in the
loader diagnosable rather than merely suspected.

## Measured properties

Read with the loader in `src/bio3dvision/blender_load.py`:

| property | value |
|---|---|
| resolution | 240 x 320 |
| EXR channels | `B`, `G`, `R`, byte-identical to each other |
| depth range | 1.702 m .. 5.000 m |
| finite fraction | 1.000 |
| `params.json` | `f_px` 311.111, `baseline` 0.065, `W` 320, `H` 240 |
| `infer_depth_convention` | `"unknown"` — see below |

The depth channel here is **not** named `Z` or `V`. bioeye's compositor wrote it
through an RGB path, so the metres sit in all three of `R`, `G` and `B`. A reader
that looks only for `Z` finds nothing in this file.

`infer_depth_convention` returns `"unknown"`, and that is the correct answer, not
a defect. The pass is planar — `render_stereo_blender.py:10` documents it as
linear camera-space Z in metres — but this is an ordinary scene of blocks, and
the inference is only meaningful on a fronto-parallel calibration render. Being
unable to diagnose the convention from this file is the guard doing its job. See
`infer_depth_convention`'s docstring for the near-miss that put the guard there.
