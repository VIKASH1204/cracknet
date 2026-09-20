"""
test_api.py — Integration test for Phase 1-3 verification.
Run from project root: venv\Scripts\python.exe test_api.py
"""

import json
import sys
import urllib.request
import urllib.error
from PIL import Image, ImageDraw
import random
import io

BASE = "http://localhost:8000"


def test_health():
    print("\n" + "="*50)
    print("TEST 1: GET /api/health")
    print("="*50)
    try:
        r = urllib.request.urlopen(f"{BASE}/api/health", timeout=10)
        data = json.loads(r.read())
        print(f"  status:           {data.get('status')}")
        print(f"  model_loaded:     {data.get('model_loaded')}")
        print(f"  weights_loaded:   {data.get('weights_loaded')}")
        print(f"  device:           {data.get('device')}")
        print(f"  mongodb_connected:{data.get('mongodb_connected')}")
        arch = data.get("model_info", {}).get("architecture", [])
        print(f"  architecture:     {len(arch)} components")
        assert data.get("status") == "online", "status must be online"
        assert data.get("model_loaded") is True, "model must be loaded"
        print("  RESULT: PASSED [OK]")
        return True
    except Exception as e:
        print(f"  RESULT: FAILED [FAIL] - {e}")
        return False


def make_test_image() -> bytes:
    """Create a synthetic green PCB test image."""
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


def test_upload_inspection():
    print("\n" + "="*50)
    print("TEST 2: POST /api/inspection/upload")
    print("="*50)

    img_bytes = make_test_image()
    boundary = "CrackXNetTestBoundary"

    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b"Content-Disposition: form-data; name=\"file\"; filename=\"test_pcb.png\"\r\n")
    parts.append(b"Content-Type: image/png\r\n\r\n")
    parts.append(img_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(f"{BASE}/api/inspection/upload", data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        r = urllib.request.urlopen(req, timeout=120)
        data = json.loads(r.read())

        print(f"  inspection_id:      {data.get('inspection_id')}")
        print(f"  pcb_id:             {data.get('pcb_id')}")
        print(f"  decision:           {data.get('decision')}")
        print(f"  defect_count:       {data.get('defect_count')}")
        print(f"  processing_time_ms: {data.get('processing_time_ms')} ms")
        print(f"  result_image_url:   {data.get('result_image_url')}")
        print(f"  explainability_url: {data.get('explainability_url')}")

        defects = data.get("defects", [])
        if defects:
            print(f"  sample defect:      {defects[0]}")

        assert data.get("inspection_id"), "inspection_id missing"
        assert data.get("decision") in ("PASS", "REWORK", "REJECT"), "bad decision"
        assert isinstance(data.get("processing_time_ms"), (int, float)), "no timing"

        print("  RESULT: PASSED [OK]")
        return True

    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  RESULT: FAILED [FAIL] - HTTP {e.code}: {body[:300]}")
        return False
    except Exception as e:
        print(f"  RESULT: FAILED [FAIL] - {e}")
        return False


def test_dashboard_summary():
    print("\n" + "="*50)
    print("TEST 3: GET /api/dashboard/summary")
    print("="*50)
    try:
        r = urllib.request.urlopen(f"{BASE}/api/dashboard/summary", timeout=10)
        data = json.loads(r.read())
        print(f"  total_inspections: {data.get('total_inspections')}")
        print(f"  pass_count:        {data.get('pass_count')}")
        print(f"  rework_count:      {data.get('rework_count')}")
        print(f"  reject_count:      {data.get('reject_count')}")
        print("  RESULT: PASSED [OK]")
        return True
    except Exception as e:
        print(f"  RESULT: FAILED [FAIL] - {e}")
        return False


def test_history():
    print("\n" + "="*50)
    print("TEST 4: GET /api/history")
    print("="*50)
    try:
        r = urllib.request.urlopen(f"{BASE}/api/history?page=1&limit=5", timeout=10)
        data = json.loads(r.read())
        print(f"  total:  {data.get('total')}")
        print(f"  page:   {data.get('page')}")
        print(f"  items:  {len(data.get('items', []))}")
        print("  RESULT: PASSED [OK]")
        return True
    except Exception as e:
        print(f"  RESULT: FAILED [FAIL] - {e}")
        return False


if __name__ == "__main__":
    print("\nCrackXNet API Integration Test")
    print("================================")

    results = [
        test_health(),
        test_upload_inspection(),
        test_dashboard_summary(),
        test_history(),
    ]

    passed = sum(results)
    total = len(results)

    print("\n" + "="*50)
    print(f"SUMMARY: {passed}/{total} tests passed")
    print("="*50)

    if passed < total:
        sys.exit(1)
