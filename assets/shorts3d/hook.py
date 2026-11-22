"""Hook GOLIDE scenes into the 3D Shorts engine (thuann-vn/claude-3d-animated-shorts, MIT) without editing its code:
one branch is added where its viewer page picks the skit, so `index.html?viewer=1&golide=<scene>` runs our scene
module (assets/shorts3d/, copied to engine/golide/) with the engine's own cast, rig, set, lights and grade.
The anchor line is checked: if the engine changes, the build stops here instead of rendering something else."""
import sys
from pathlib import Path

ANCHOR = "  if (!Q.has('skit')) loop(); else {"
CTX = ("THREE, Q, SR, base, scene, camera, renderer, post, U, hemi, sun, SUNDIR, setLook, resetScene, face, place, idle, "
       "arm, leg, Lw, dirW, headC, yawTo, ease, eio, clamp, lerp, V, look, hips, headTurn, ALL, OUTF, thua, chief, ti, ex, "
       "O: OFF_O, FY, Z, ui, WW, HH, FACES, FT")
HOOK = ("  if (Q.has('golide')) { const { run } = await import('./golide/scene.js'); await run({ " + CTX + " }); }\n"
        "  else if (!Q.has('skit')) loop(); else {")

main = Path(sys.argv[1])
src = main.read_text(encoding="utf-8")
if src.count(ANCHOR) != 1:
    sys.exit(f"hook: the engine's skit branch moved ({src.count(ANCHOR)} matches) in {main}; update assets/shorts3d/hook.py")
main.write_text(src.replace(ANCHOR, HOOK), encoding="utf-8")
print("hook: GOLIDE scenes wired into", main)
