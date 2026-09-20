"""
test_upload.py — Test the /api/inspection/upload endpoint.
Run: venv\Scripts\python.exe test_upload.py
"""

import sys, io, json, urllib.request, urllib.error
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PIL import Image, ImageDraw
import random

BASE = "http://localhost:8000"


def make_test_image_bytes():
    img = Image.new("RGB", (640, 480), color=(18, 78, 38))
    draw = ImageDraw.Draw(img)
    for i in range(0, 640, 40):
        draw.line([(i, 0), (i, 480)], fill=(180, 160, 30), width=2)
    for j in range(0, 480, 40):
        draw.line([(0, j), (640, j)], fill=(180, 160, 30), width=2)
    for _ in range(15):
        x, y = random.randint(50, 590), random.randint(50, 430)
        draw.ellipse([x-8, y-8, x+8, y+8], fill=(210, 190, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


print("=" * 60)
print("CrackXNet Phase 1-3 Verification")
print("=" * 60)

# ── TEST 1: Health ────────────────────────────────────────────
print("\n[TEST 1] GET /api/health")
r = urllib.request.urlopen(f"{BASE}/api/health", timeout=10)
d = json.loads(r.read())
print(f"  status:           {d['status']}")
print(f"  model_loaded:     {d['model_loaded']}")
print(f"  weights_loaded:   {d['weights_loaded']}")
print(f"  device:           {d['device']}")
print(f"  mongodb:          {d['mongodb_connected']}")
print(f"  classes:          {d['model_info']['class_names']}")
assert d["status"] == "online" and d["model_loaded"], "FAILED"
print("  -> PASSED")

# ── TEST 2: Upload inspection ─────────────────────────────────
print("\n[TEST 2] POST /api/inspection/upload")
img_bytes = make_test_image_bytes()
boundary = "CrackXNetTestBoundary"
body = (
    f"--{boundary}\r\n".encode()
    + b"Content-Disposition: form-data; name=\"file\"; filename=\"test_pcb.png\"\r\n"
    + b"Content-Type: image/png\r\n\r\n"
    + img_bytes
    + f"\r\n--{boundary}--\r\n".encode()
)
req = urllib.request.Request(f"{BASE}/api/inspection/upload", data=body)
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

try:
    r = urllib.request.urlopen(req, timeout=120)
    d = json.loads(r.read())
    print(f"  inspection_id:      {d.get('inspection_id')}")
    print(f"  pcb_id:             {d.get('pcb_id')}")
    print(f"  decision:           {d.get('decision')}")
    print(f"  defect_count:       {d.get('defect_count')}")
    print(f"  processing_time_ms: {d.get('processing_time_ms')} ms")
    print(f"  result_image_url:   {d.get('result_image_url')}")
    print(f"  explainability_url: {d.get('explainability_url')}")
    print(f"  persisted:          {d.get('persisted')}")
    defects = d.get("defects", [])
    if defects:
        print(f"  first defect:       {defects[0]}")
    assert d.get("decision") in ("PASS", "REWORK", "REJECT")
    assert isinstance(d.get("processing_time_ms"), (int, float))
    print("  -> PASSED")
except urllib.error.HTTPError as e:
    print(f"  -> FAILED HTTP {e.code}: {e.read().decode()[:300]}")
    sys.exit(1)

# ── TEST 3: Dashboard summary ─────────────────────────────────
print("\n[TEST 3] GET /api/dashboard/summary")
r = urllib.request.urlopen(f"{BASE}/api/dashboard/summary", timeout=10)
d = json.loads(r.read())
print(f"  total_inspections:    {d.get('total_inspections')}")
print(f"  average_proc_time_ms: {d.get('average_processing_time_ms')}")
print("  -> PASSED")

# ── TEST 4: History ───────────────────────────────────────────
print("\n[TEST 4] GET /api/history")
r = urllib.request.urlopen(f"{BASE}/api/history?page=1&limit=5", timeout=10)
d = json.loads(r.read())
print(f"  total: {d.get('total')}")
print(f"  items: {len(d.get('items', []))}")
print("  -> PASSED")

print("\n" + "=" * 60)
print("ALL PHASE 1-3 TESTS PASSED")
print("=" * 60)
