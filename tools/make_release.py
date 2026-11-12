#!/usr/bin/env python3
"""Build dist/nonplanar_top-<version>.zip with everything a user needs, and
dist/nonplanar_top-<version>-printables.zip without the .bat installer (Printables
rejects archives containing .bat files) but with printables/INSTALL.txt."""
import os, re, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ver = re.search(r'VERSION = "([^"]+)"', open(os.path.join(ROOT, "nonplanar_top.py"), encoding="utf-8").read()).group(1)
files = ["nonplanar_top.py", "nonplanar_top.ini", "install_windows.bat", "requirements.txt",
         "README.md", "LICENSE", "CREDITS.md", "CHANGELOG.md", "profiles/NONPLANAR_print_profile.ini",
         "samples/README.md", "samples/coupon_dome_50mm.stl", "samples/coupon_ramp_2deg.stl",
         "samples/coupon_wave_80mm.stl", "samples/nonplanar_top_test_coupons.3mf"]
files += ["docs/" + f for f in sorted(os.listdir(os.path.join(ROOT, "docs"))) if f.endswith(".md")]
files += ["docs/images/" + f for f in sorted(os.listdir(os.path.join(ROOT, "docs/images")))]
os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
def build(name, fl, extra=()):
    out = os.path.join(ROOT, "dist", name)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in fl:
            z.write(os.path.join(ROOT, f), "nonplanar_top/" + f)
        for src, dst in extra:
            z.write(os.path.join(ROOT, src), "nonplanar_top/" + dst)
    print(out, os.path.getsize(out) // 1024, "KB")
build("nonplanar_top-%s.zip" % ver, files)
build("nonplanar_top-%s-printables.zip" % ver, [f for f in files if not f.endswith(".bat")],
      [("printables/INSTALL.txt", "INSTALL.txt")])
