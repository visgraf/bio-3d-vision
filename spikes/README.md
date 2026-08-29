# spikes/

Where you try things. This is the low-ceremony part of the repository, and the
low ceremony is the point: an idea should be cheap to test and cheap to throw
away.

## The rules

**Git-tracked.** Spikes are committed. A spike that lives only on your disk
cannot be pointed at, and the whole reason this directory exists is so that "I
tried that, here is what happened" is a thing you can show.

**No ADR. No findings entry. No definition of done.** None of them apply here.
Do not write an ADR *about* a spike — an ADR is written after the thing it
decides has been tried, so the spike is what you do *before* the ADR, and the ADR
comes after if the answer was worth keeping.

**No tests required.** Write them if they help you; nothing checks.

**Not importable.** Nothing in `src/` or `experiments/` may import from here.
Enforced by `tests/test_scaffold.py`, which CI runs. If the library needs
something a spike has, that is the signal to write it properly in `src/` — with
tests — not to import it from here.

**The only permitted output is a decision or a deletion.**

- *A decision:* write what you learned into `docs/state.yaml` — an open decision
  resolved, a new one opened, or a foreclosure with its reason — and then delete
  the spike.
- *A deletion:* it did not work, or it stopped being interesting. Delete it. The
  git history keeps it if anyone ever wants it.

A spike that is neither — still sitting there, not deciding anything, not
deleted — is the failure mode this directory has. It should go. Ask, and then
delete it.

## Naming

`spikes/<short-question>/`. Name it after the question you are answering, not
the technique you are using: `does-the-fixture-need-occlusion/`, not
`numpy-warp-test/`. When the question is answered the directory's name tells you
the spike is finished.
