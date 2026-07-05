# LabJack T4 TTL 트리거 유틸리티

# 핀 구성 (총 9라인):
#   EIO0~EIO7 (8핀) : 트리거 코드값 (8비트 데이터)
#   CIO0       (1핀) : trigger latch (strobe) — Natus Quantum이 rising edge에서 데이터 캡처


try:
    from labjack import ljm
    _LJM_AVAILABLE = True
except ImportError:
    _LJM_AVAILABLE = False

import time

# 펄스 타이밍 허용 오차 (초). 이 값을 초과하면 TIMING MISMATCH 로그 출력.
_PULSE_TOLERANCE_S = 0.001  # 1 ms

# Trigger latch 핀: CIO0 (CIO_STATE 비트 0)
_LATCH_CIO_STATE = 0x01  # CIO0 = HIGH


# ============================================================================
# 트리거 코드 상수
# ============================================================================

TRIG_RESET            = 0

# =========================================
# check trial (phase1 – competence)
# =========================================

ANIMAL_IDX        = {'A': 0, 'B': 1, 'C': 2, 'D': 3}

TRIG_P1_STIMULUS  = 0x10   # 0001_0000  stimulus onset
TRIG_P1_CHOICE1   = 0x14   # 0001_01xx  + ANIMAL_IDX → 0x14~0x17
TRIG_P1_CHOICE2   = 0x18   # 0001_10xx  + ANIMAL_IDX → 0x18~0x1B
TRIG_P1_FEEDBACK  = 0x1C   # 0001_1100

# =========================================
# main belief trial (phase2 – synergy)
# =========================================

TRIG_P2_STIMULUS  = 0x20   # 0010_0000
TRIG_P2_CHOICE1   = 0x24   # 0010_01xx  + ANIMAL_IDX → 0x24~0x27
TRIG_P2_CHOICE2   = 0x28   # 0010_10xx  + ANIMAL_IDX → 0x28~0x2B
TRIG_P2_FEEDBACK  = 0x2C   # 0010_1100

# =========================================
# no-cue choice trial (phase3 – choice task)
# =========================================

TRIG_P3_STIMULUS  = 0x30   # 0011_0000  stimulus onset
TRIG_P3_CHOICE1   = 0x34   # 0011_01xx  + ANIMAL_IDX → 0x34~0x37
TRIG_P3_CHOICE2   = 0x38   # 0011_10xx  + ANIMAL_IDX → 0x38~0x3B
TRIG_P3_FEEDBACK  = 0x3C   # 0011_1100

# =========================================
# trial boundary
# =========================================

TRIG_TRIAL_START      = 0x40
TRIG_TRIAL_END        = 0x41




# ============================================================================
# 연결 관리
# ============================================================================

def init_labjack(device: str = "T4",
                 connection: str = "USB",
                 identifier: str = "ANY") -> int | None:
    # LabJack T4 연결
    if not _LJM_AVAILABLE:
        print("[LabJack] ljm 라이브러리를 찾을 수 없습니다. 트리거가 비활성화됩니다.")
        return None

    try:
        handle = ljm.openS(device, connection, identifier)
        info   = ljm.getHandleInfo(handle)
        print(f"[LabJack] 연결 성공: {info}")

        # EIO 핀 초기화 (8비트 데이터 라인)
        #ljm.eWriteName(handle, "EIO_INHIBIT",   0)     # 출력 활성화 (기본값이지만 명시적으로 설정)
        ljm.eWriteName(handle, "EIO_DIRECTION", 0xFF)  # 모든 EIO 핀 출력
        ljm.eWriteName(handle, "EIO_STATE",     0)     # 초기값 0

        # CIO 핀 초기화 (CIO0 = trigger latch)
        #ljm.eWriteName(handle, "CIO_INHIBIT",   0)     # 출력 활성화
        ljm.eWriteName(handle, "CIO_DIRECTION", 0x0F)  # CIO0~3 모두 출력
        ljm.eWriteName(handle, "CIO_STATE",     0)     # 초기값 0 (latch LOW)

        print("[LabJack] EIO(데이터 8핀) + CIO0(trigger latch) 초기화 완료")
        return handle

    except Exception as e:
        print(f"[LabJack] 연결 실패: {e}")
        return None


def close_labjack(handle: int | None):
    if handle is None or not _LJM_AVAILABLE:
        return
    try:
        ljm.eWriteName(handle, "CIO_STATE", 0)
        ljm.eWriteName(handle, "EIO_STATE", 0)
        ljm.close(handle)
        print("[LabJack] 연결 종료")
    except Exception as e:
        print(f"[LabJack] 종료 오류: {e}")


# ============================================================================
# 트리거 전송
# ============================================================================

def send_trigger(handle: int | None, code: int, pulse_s: float = 0.005):
    """EIO 포트로 TTL 트리거 펄스 전송 (블로킹, perf_counter busy-wait).

    전송 순서:
      EIO_STATE = code  →  CIO0(latch) HIGH  →  busy-wait  →  CIO0 LOW  →  EIO_STATE = 0
    Natus Quantum은 CIO0의 rising edge에서 EIO 데이터를 캡처한다.
    """
    if handle is None or not _LJM_AVAILABLE:
        return
    try:
        t_start = time.perf_counter()
        #print(f"[LabJack] SEND code={hex(code)} ({t_start:.4f}s)")
        ljm.eWriteName(handle, "EIO_STATE", int(code))
        ljm.eWriteName(handle, "CIO_STATE", _LATCH_CIO_STATE)  # latch HIGH (rising edge → Natus 캡처)
        while time.perf_counter() - t_start < pulse_s:
            pass
        ljm.eWriteName(handle, "CIO_STATE", 0)   # latch LOW
        ljm.eWriteName(handle, "EIO_STATE", 0)   # 데이터 클리어
        t_actual = time.perf_counter() - t_start
        if abs(t_actual - pulse_s) > _PULSE_TOLERANCE_S:
            '''
            print(
                f"[TIMING MISMATCH] send_trigger code={code}: "
                f"expected {pulse_s * 1000:.2f} ms, "
                f"actual {t_actual * 1000:.2f} ms "
                f"(diff {(t_actual - pulse_s) * 1000:+.2f} ms)"
            )
            '''
    except Exception as e:
        print(f"[LabJack] 트리거 전송 오류 (code={code}): {e}")


def send_trigger_async(handle: int | None, code: int):
    """EIO_STATE + CIO0(latch) 설정 (비블로킹). 리셋은 호출자가 reset_trigger()로 처리."""
    if handle is None or not _LJM_AVAILABLE:
        return
    try:
        ljm.eWriteName(handle, "EIO_STATE", int(code))
        ljm.eWriteName(handle, "CIO_STATE", _LATCH_CIO_STATE)  # latch HIGH
    except Exception as e:
        print(f"[LabJack] 비동기 트리거 오류 (code={code}): {e}")


def reset_trigger(handle: int | None):
    """CIO0(latch)를 LOW로 내리고 EIO_STATE를 0으로 리셋합니다."""
    if handle is None or not _LJM_AVAILABLE:
        return
    try:
        ljm.eWriteName(handle, "CIO_STATE", 0)   # latch LOW
        ljm.eWriteName(handle, "EIO_STATE", 0)   # 데이터 클리어
    except Exception as e:
        print(f"[LabJack] 리셋 오류: {e}")
