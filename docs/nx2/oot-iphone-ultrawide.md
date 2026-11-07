# Ocarina of Time: iPhone 13 Pro ultrawide investigation

Status: research tooling only. No working camera, HUD, or cutscene patch has
been identified or tested. The emulator source does not contain the game's
camera implementation. The game is not installed in the cloud workspace.

## Exact target

Landscape output is 2532 x 1170, or 422:195 (2.164102564:1). Use this exact
ratio rather than rounded 19.5:9 or 21:9. For a conventional perspective camera
that preserves vertical FOV, the horizontal projection coefficient would be
multiplied by 520/633 (approximately 0.821485), relative to 16:9. This is a
mathematical target, not evidence that any particular game value is the camera.

## What the fork already does

- `src/core/frontend/framebuffer_layout.cpp`: `Stretch` fills the window;
  the 21:9 option only changes presentation bounds. Neither expands game FOV.
- `src/core/file_sys/patch_manager.cpp`: built-in Ocarina patches target
  title `0400486024DEC000`, module `main`, build ID
  `E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348`. Max Resolution and Dynamic FPS
  are unrelated to aspect ratio. A future built-in camera patch should use
  the existing build-ID/original-byte validation and respect external mods.
- `src/core/loader/nso.cpp` and `PatchManager::PatchNSO`: the existing
  decompressed dump contains an NSO header followed by the module memory image.
  A module offset maps to dump/IPS offset `module_offset + 0x100`, even though
  the header retains its original compressed-file offsets and flags.

## Get the missing evidence without uploading game files

1. In Lichii's filesystem settings, enable **Dump Decompressed NSOs**. Launch
   Ocarina, then disable that option after the dump has been written.
2. Under the configured Dump Root, locate
   `0400486024DEC000/nso/main-<build ID>.nso`. The log also records
   `Dumping NSO for name=main` and the build ID. Keep the dump on your PC.
3. With Python 3, run this read-only script there:

   ```powershell
   py -3 tools/nx2/oot_aspect_probe.py "C:\path\main-BUILDID.nso" --output iphone-aspect-report.json
   ```

The report contains build ID, dump hash, candidate offsets, aspect literals and
direct AArch64 floating-point literal-load references. It contains no arbitrary
game data or instruction windows. The script never writes to the dump, installs
a mod, or generates a cheat. It only accepts the **Lichii dump layout**; do not
pass an ordinary compressed ExeFS NSO.

An empty report is possible: aspect may be computed from viewport dimensions,
stored in engine resources, or constructed by instructions. Candidate literals
must be traced to camera construction and tested individually; replacing all
16:9 values can break videos, UI or unrelated code. Direct literal references
are only a starting point. Existing `nso_dis.py`, `nso_syms.py`, GDB and the
opt-in live debug server support the next investigation.

## Verification required before calling a patch seamless

Validate a reversible camera experiment in the same scene at 16:9 and 422:195:
objects retain their proportions, vertical framing stays constant, and more
scenery appears at both sides. Then check visibility/culling, shadows, aiming,
world markers, menus, subtitles, HUD and screen-space effects. Trace any failures
separately. Pre-rendered 16:9 movies require an explicit crop or stretch policy
to fill the phone; widening the 3D camera cannot add scenery to a recorded video.

For streaming, set the captured physical/virtual host display and Moonlight's
stream resolution to 2532 x 1170, use fullscreen and `Stretch` in Lichii once
the camera is corrected. Confirm Moonlight uses the full landscape display
rather than a safe-area inset; the notch still physically obscures image pixels.
An emulator patch cannot change the iOS client's presentation or the host display.

## Research sources

Upstream Eglantine `nx2`, branch names and open/closed Ocarina/aspect PRs were
surveyed on 2026-11-07; no existing verified aspect patch was found.

- <https://github.com/zortos293/Lichii/issues/136>: open ultrawide feature request.
- <https://github.com/zortos293/Lichii/pull/124>: Max Resolution patch precedent;
  its diff disables dynamic resolution, not aspect correction.

Tests use synthetic module dumps only:
`python3 -m unittest discover -s tools/nx2 -p test_oot_aspect_probe.py -v`.
