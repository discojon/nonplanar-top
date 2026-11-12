#!/usr/bin/env python3
"""Build dist/nonplanar_top-<version>.zip with everything a user needs."""
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
out = os.path.join(ROOT, "dist", "nonplanar_top-%s.zip" % ver)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(os.path.join(ROOT, f), "nonplanar_top/" + f)
print(out, os.path.getsize(out) // 1024, "KB")
