"""
Neon connection smoke test — run this BEFORE the real task to confirm the phone
is reachable and a recording is active.

Prereqs:
  1. pip install pupil-labs-realtime-api
  2. Neon glasses plugged into Companion phone
  3. Phone and this PC on the SAME WiFi
  4. Recording STARTED in the Companion app

Run:  python neon_check.py
"""

from pupil_labs.realtime_api.simple import discover_one_device


def check_neon_ready(timeout_s: float = 10.0) -> bool:
    """Return True if a Neon device is reachable and a recording is active."""
    dev = discover_one_device(max_search_duration_seconds=timeout_s)
    if dev is None:
        return False
    try:
        ev = dev.send_event("NEON_CHECK")
        ready = bool(getattr(ev, "recording_id", None))
    except Exception:
        ready = False
    finally:
        dev.close()
    return ready


def main():
    print("• Companion 장치 검색 중 (같은 WiFi) ...")
    dev = discover_one_device(max_search_duration_seconds=10.0)
    if dev is None:
        print("✗ 장치를 찾지 못함 — 폰 WiFi / Companion 앱을 확인하세요.")
        return
    print(f"✓ 연결: {getattr(dev, 'phone_name', '?')}  "
          f"glasses={getattr(dev, 'serial_number_glasses', '?')}")

    try:
        est = dev.estimate_time_offset()
        print(f"• clock offset ≈ {est.time_offset_ms.mean:.1f} ms "
              f"(±{est.time_offset_ms.std:.1f})")
    except Exception as e:
        print(f"• clock offset 추정 실패(무시 가능): {e}")

    ev = dev.send_event("NEON_CHECK")
    rec = getattr(ev, "recording_id", None)
    if rec:
        print(f"✓ active recording — recording_id = {rec}")
        print("  → 준비 완료.  python main.py 로 실행하세요.")
    else:
        print("✗ recording_id 없음 — Companion 앱에서 녹화를 먼저 시작하세요.")

    dev.close()


if __name__ == "__main__":
    main()
