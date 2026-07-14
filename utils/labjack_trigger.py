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

TRIG_RESET = 0

# =========================================
# Animal index — 24마리 고유 ID (동물명 기준)
#   Group 1 (0- 3): duck, frog, panda, rabbit
#   Group 2 (4- 7): bear, cat, chicken, cow
#   Group 3 (8-11): horse, koala, lion, tiger
#   Group 4 (12-15): deer, dog, elephant, fish
#   Group 5 (16-19): fox, hippo, kappa, mouse
#   Group 6 (20-23): otter, seal, sealion, sheep
# =========================================

ANIMAL_IDX = {
    'duck': 0,  'frog': 1,     'panda': 2,    'rabbit': 3,
    'bear': 4,  'cat': 5,      'chicken': 6,  'cow': 7,
    'horse': 8, 'koala': 9,    'lion': 10,    'tiger': 11,
    'deer': 12, 'dog': 13,     'elephant': 14,'fish': 15,
    'fox': 16,  'hippo': 17,   'kappa': 18,   'mouse': 19,
    'otter': 20,'seal': 21,    'sealion': 22, 'sheep': 23,
}

# =========================================
# Stimulus onset — phase를 인코딩
# =========================================

TRIG_P3_STIMULUS = 30   # Phase 3 (choice)

# =========================================
# Choice — phase + choice 순서 + 동물 인코딩
#   base + ANIMAL_IDX (0-23) → 동물명으로 조회
#
#   P1: choice1 = 41-64,  choice2 =  65-88
#   P2: choice1 = 89-112, choice2 = 113-136
#   P3: choice1 = 137-160,choice2 = 161-184
# =========================================

TRIG_P1_CHOICE1 = 41
TRIG_P1_CHOICE2 = 65
TRIG_P2_CHOICE1 = 89
TRIG_P2_CHOICE2 = 113
TRIG_P3_CHOICE1 = 137
TRIG_P3_CHOICE2 = 161

# =========================================
# Feedback — phase를 인코딩
# =========================================

TRIG_P1_FEEDBACK = 191
TRIG_P2_FEEDBACK = 192
TRIG_P3_FEEDBACK = 193

# =========================================
# Trial boundary — phase를 인코딩
# =========================================

TRIG_P1_TRIAL_START = 211
TRIG_P2_TRIAL_START = 212
TRIG_P3_TRIAL_START = 213
TRIG_P1_TRIAL_END   = 231
TRIG_P2_TRIAL_END   = 232
TRIG_P3_TRIAL_END   = 233




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

def send_trigger(handle: int | None, code: int, pulse_s: float = 0.010):
    """EIO 포트로 TTL 트리거 펄스 전송 (블로킹, perf_counter busy-wait).

    전송 순서:
      EIO_STATE = code  →  2ms busy-wait  →  CIO0(latch) HIGH  →
      pulse_s busy-wait  →  CIO0 LOW  →  1ms busy-wait  →  EIO_STATE = 0

    Natus Quantum은 CIO0의 rising edge에서 EIO 데이터를 캡처한다.
    busy-wait를 사용하는 이유: Windows의 time.sleep() 최소 해상도가
    ~15ms이므로 sleep(0.005)가 실제로 5ms를 보장하지 않는다.
    """
    if handle is None or not _LJM_AVAILABLE:
        return
    try:
        t_start = time.perf_counter()
        print(f"[LabJack] SEND code={code} ({t_start:.4f}s)")
        # 1. 데이터 설정
        ljm.eWriteName(handle, "EIO_STATE", int(code))

        # 2. EIO 안정화 대기 (USB 왕복 후 핀 안정 보장)
        _t = time.perf_counter()
        while time.perf_counter() - _t < 0.002:
            pass

        # 3. Latch HIGH → Natus가 rising edge에서 EIO 값 캡처
        ljm.eWriteName(handle, "CIO_STATE", _LATCH_CIO_STATE)

        # 4. 펄스 유지
        _t = time.perf_counter()
        while time.perf_counter() - _t < pulse_s:
            pass

        # 5. Latch LOW → 다음 트리거를 위한 falling edge
        ljm.eWriteName(handle, "CIO_STATE", 0)

        # 6. hold time 후 데이터 클리어 (falling edge 직후 클리어 방지)
        _t = time.perf_counter()
        while time.perf_counter() - _t < 0.001:
            pass

        ljm.eWriteName(handle, "EIO_STATE", 0)

    except Exception as e:
        print(f"[LabJack] 트리거 전송 오류 (code={code}): {e}")


def send_trigger_async(handle: int | None, code: int):
    """EIO_STATE + CIO0(latch) 설정 (비블로킹). 리셋은 호출자가 reset_trigger()로 처리."""
    if handle is None or not _LJM_AVAILABLE:
        return
    try:
        print(f"[LabJack] SEND_ASYNC code={code} ({time.perf_counter():.4f}s)")
        ljm.eWriteNames(handle, 2,
            ["EIO_STATE", "CIO_STATE"],
            [float(code), float(_LATCH_CIO_STATE)])   # EIO + latch HIGH, 단일 USB 패킷
    except Exception as e:
        print(f"[LabJack] 비동기 트리거 오류 (code={code}): {e}")


def reset_trigger(handle: int | None):
    """CIO0(latch)를 LOW로 내리고 EIO_STATE를 0으로 리셋합니다."""
    if handle is None or not _LJM_AVAILABLE:
        return
    try:
        ljm.eWriteNames(handle, 2,
            ["CIO_STATE", "EIO_STATE"],
            [0.0, 0.0])   # latch LOW + 데이터 클리어, 단일 USB 패킷
    except Exception as e:
        print(f"[LabJack] 리셋 오류: {e}")
