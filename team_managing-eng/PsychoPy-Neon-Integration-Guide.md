# PsychoPy-Neon Integration Guide



핵심 연결 구조는 다음과 같다.

```text
AprilTag = 장면 영상 속 모니터 위치를 찾기 위한 표식
Neon event = gaze를 실험 단계와 연결하기 위한 timestamp
SECTION_START / END = Cloud에서 분석 구간을 나누기 위한 경계
neon_event_log.xlsx = 이벤트 전송 검증용 로컬 로그
session_id + recording_id = 행동 데이터와 Neon 녹화 연결 키
```

## 1. 필요한 파일 구조

PsychoPy 실험에 적용할 때는 Neon 전송 코드를 태스크 본문에 직접 흩뿌리지 말고, 공통 모듈 하나로 분리하는 것이 좋다.

예를 들어 다음 파일을 만들 수 있다.

```text
utils/neon_client.py
```

이 파일 안에는 두 종류의 client가 있다.

```python
NeonEventClient  # 실제 Neon Companion으로 이벤트를 보내는 client
NullNeonClient   # USE_NEON=False일 때 아무 것도 하지 않는 대체 client
```

이 구조를 쓰면 Neon을 켰을 때와 껐을 때의 실행 경로를 하나로 유지할 수 있다.

```python
if USE_NEON:
    neon_client = NeonEventClient(...)
else:
    neon_client = NullNeonClient()
```

이렇게 하면 태스크 함수 내부에서는 항상 `neon_client`를 받게 만들 수 있다.

```python
def run_trial(win, trial, neon_client):
    neon_client.call_on_flip(win, "TRIAL_001_STIMULUS", task_type="trial")
```

## 2. config에 Neon 설정 추가

태스크 설정 파일에는 최소한 다음 값이 필요하다.

```python
USE_NEON = True
NEON_DISCOVERY_TIMEOUT_S = 10.0
NEON_RETRY_INTERVAL_S = 1.0
NEON_SHUTDOWN_FLUSH_TIMEOUT_S = 5.0
```

AprilTag 위치와 크기도 config에서 관리한다.

```python
NEON_APRILTAG_SIZE = 0.10
NEON_APRILTAG_POSITIONS = (
    (-0.72, 0.44),
    (0.00, 0.44),
    (0.72, 0.44),
    (-0.83, 0.00),
    (0.83, 0.00),
    (0.00, -0.44),
    (0.72, -0.44),
)
```

아래 예시는 PsychoPy `height` 단위를 기준으로 한다. 실험 코드에서 `pix`, `norm`, `height` 중 어떤 단위를 쓰는지 확인하고, AprilTag 위치도 같은 좌표계에 맞춰야 한다.

## 3. session_id 만들기

Neon 녹화와 PsychoPy 행동 결과를 연결하려면 참가자 ID만으로는 부족하다. 같은 참가자가 여러 번 실행될 수 있으므로 실행 시각 기반 `session_id`를 만든다.

```python
from datetime import datetime

subject_id = input("Subject ID: ")
session_id = datetime.now().strftime("%Y%m%dT%H%M%S")
```

그리고 `metadata.txt`에 같이 저장한다.

```text
Subject ID: sub001
Session ID: 20260724T143012
```

결과 파일, event log, metadata에는 `subject_id`, `session_id`를 모두 넣어야 한다.

## 4. Neon session 시작

Neon Companion 녹화는 PsychoPy 실행 전에 휴대폰에서 수동으로 시작한다. PsychoPy 쪽에서는 첫 자극 전에 Neon 장치와 연결하고, active recording이 있는지 확인한다.

```python
if USE_NEON:
    neon_client = NeonEventClient(
        discovery_timeout_s=NEON_DISCOVERY_TIMEOUT_S,
        retry_interval_s=NEON_RETRY_INTERVAL_S,
    )
    neon_recording_id = neon_client.start_session(subject_id, session_id)
else:
    neon_client = NullNeonClient()
    neon_recording_id = None
```

`start_session()`은 다음 일을 한다.

```text
1. 같은 네트워크에서 Neon Companion 장치 검색
2. 장치가 0대 또는 여러 대면 첫 자극 전에 중단
3. PC 시간과 Companion 시간 offset 추정
4. SESSION_START_<subject_id>_<session_id> 이벤트 전송
5. returned recording_id 확인
6. recording_id가 없으면 active recording이 아니므로 중단
```

`recording_id`는 이후 모든 행동 결과와 로그에 저장한다.

## 5. AprilTag 생성

AprilTag는 장면 영상 속에서 실험 모니터의 위치를 찾기 위한 표식이다. PsychoPy window가 만들어진 뒤 한 번 생성하고, 실험 내내 `AutoDraw`로 유지한다.

아래처럼 `create_neon_apriltags()` 같은 함수를 만들어 window 생성 직후 호출한다.

```python
from psychopy_eyetracker_pupil_labs.pupil_labs.stimuli import AprilTagStim

tags = []
for marker_id, pos in enumerate(NEON_APRILTAG_POSITIONS):
    tag = AprilTagStim(
        win=win,
        marker_id=marker_id,
        units="height",
        pos=pos,
        size=(NEON_APRILTAG_SIZE, NEON_APRILTAG_SIZE),
        interpolate=False,
        autoLog=False,
    )
    tag.setAutoDraw(True)
    tags.append(tag)
```

적용 원칙은 다음과 같다.

```text
AprilTag는 자극과 겹치지 않는 화면 가장자리에 둔다.
최소 4개 이상을 유지한다.
각 marker_id는 서로 달라야 한다.
실험 중간에 사라지지 않게 AutoDraw로 유지한다.
SEEG optical marker가 있다면 위치가 겹치지 않게 한다.
```

화면 layout이 다르면 AprilTag 위치만 다시 잡으면 된다. Neon event 전송 구조는 그대로 사용할 수 있다.

## 6. Neon event는 flip 시점에 넣기

PsychoPy에서 자극은 코드를 실행한 순간이 아니라 `win.flip()` 순간에 화면에 나타난다. 따라서 자극 onset 이벤트는 일반 코드에서 바로 보내면 안 되고 `win.callOnFlip()`에 등록해야 한다.

helper는 다음 형태로 둘 수 있다.

```python
neon_client.call_on_flip(
    win,
    "TRIAL_001_QUESTION",
    task_type="trial",
    phase="question",
    trial_index=1,
)
```

`call_on_flip()` 내부에서는 실제 네트워크 전송을 하지 않고 `enqueue_events()`만 예약한다.

```python
def call_on_flip(self, win, event_names, **metadata):
    win.callOnFlip(self.enqueue_events, event_names, metadata=metadata)
```

이 구조를 쓰는 이유는 다음과 같다.

```text
flip callback에서는 timestamp 기록과 queue 삽입만 한다.
Neon 전송은 별도 worker thread가 처리한다.
네트워크 지연이 PsychoPy frame timing을 막지 않는다.
전송 실패 시 원래 timestamp를 유지하고 재시도할 수 있다.
```

## 7. SECTION_START / END로 분석 구간 만들기

Cloud에서 gaze를 단계별로 자르려면 구간 경계 이벤트가 필요하다. 이때 `SECTION_START / END`는 구간의 시작과 끝이고, `TRIAL_001_QUESTION` 같은 이벤트는 그 구간이 무엇인지 알려주는 식별자다.

예를 들어 한 trial을 5개 section으로 나누면 다음과 같다.

```text
TRIAL_SECTION_START + TRIAL_001_QUESTION
TRIAL_SECTION_END

TRIAL_SECTION_START + TRIAL_001_PREMISE
TRIAL_SECTION_END

TRIAL_SECTION_START + TRIAL_001_OPTION_LEFT
TRIAL_SECTION_END

TRIAL_SECTION_START + TRIAL_001_OPTION_RIGHT
TRIAL_SECTION_END

TRIAL_SECTION_START + TRIAL_001_CHOICE
TRIAL_SECTION_END
```

이 패턴은 helper로 만들면 재사용하기 쉽다.

```python
TRIAL_PHASES = (
    "question",
    "premise",
    "option_left",
    "option_right",
    "choice",
)

def trial_section_transition_events(trial_index: int, phase: str):
    events = []
    if phase != "question":
        events.append("TRIAL_SECTION_END")
    events.extend((
        "TRIAL_SECTION_START",
        f"TRIAL_{trial_index:03d}_{phase.upper()}",
    ))
    return tuple(events)
```

trial 코드에서는 각 단계 첫 frame에서 다음처럼 호출한다.

```python
if frame_count == 0:
    neon_client.call_on_flip(
        win,
        trial_section_transition_events(index, "question"),
        task_type="trial",
        phase="question",
        trial_index=index,
    )
```

다음 단계로 넘어갈 때는 이전 section의 END와 새 section의 START를 같은 flip timestamp에 넣는다.

```python
neon_client.call_on_flip(
    win,
    trial_section_transition_events(index, "premise"),
    task_type="trial",
    phase="premise",
    trial_index=index,
)
```

이렇게 하면 Cloud에서 section을 trial 단계별로 나눌 수 있다.

## 8. 응답 이벤트는 실제 키가 감지된 시점에 넣기

자극 onset은 `call_on_flip()`으로 넣지만, 응답은 참가자 키 입력이 감지된 시점에 넣는다.

예시:

```python
if response_key == "left":
    neon_client.enqueue_events(
        ("TRIAL_001_RESPONSE_LEFT_CORRECT", "TRIAL_SECTION_END"),
        metadata={
            "task_type": "trial",
            "phase": "choice",
            "trial_index": 1,
        },
    )
```

무응답이면 timeout이 끝나는 시점에 별도 이벤트를 넣는다.

```python
neon_client.enqueue_events(
    ("TRIAL_001_NO_RESPONSE", "TRIAL_SECTION_END"),
    metadata={
        "task_type": "trial",
        "phase": "choice",
        "trial_index": 1,
    },
)
```

응답 이벤트와 `SECTION_END`를 같이 넣으면 선택 구간이 응답 시점에서 닫힌다.

## 9. 이벤트 로그 저장

Neon event는 Cloud에 보내는 것과 별도로 로컬에 저장해야 한다. 그래야 Cloud 수신 여부, 재시도 여부, timestamp 변환을 나중에 확인할 수 있다.

로그 열은 다음처럼 둘 수 있다.

```python
LOG_COLUMNS = (
    "event_sequence",
    "session_id",
    "subject_id",
    "recording_id",
    "task_type",
    "phase",
    "trial_index",
    "attempt_index",
    "event_name",
    "host_timestamp_unix_ns",
    "companion_timestamp_unix_ns",
    "clock_offset_ns",
    "send_attempt",
    "send_success",
    "retried",
    "send_error",
)
```

각 이벤트는 처음 queue에 들어갈 때 한 번 로그가 남는다.

```text
send_attempt = 0
send_success = False
send_error = Queued
```

실제 전송이 성공하면 같은 `event_sequence`에 성공 행이 추가된다.

```text
send_attempt = 1
send_success = True
send_error =
```

전송 실패 후 재시도되면 `retried=True`가 된다.

로그 저장 예시는 다음과 같다.

```python
def save_diagnostic_logs(save_directory, neon_event_log):
    pd.DataFrame(neon_event_log, columns=LOG_COLUMNS).to_excel(
        os.path.join(save_directory, "neon_event_log.xlsx"),
        index=False,
    )
```

실험 종료 시에는 `close()`로 남은 이벤트 전송을 기다린 뒤 로그를 저장한다.

```python
flushed = neon_client.close(NEON_SHUTDOWN_FLUSH_TIMEOUT_S)
save_diagnostic_logs(save_directory, neon_client.event_log)
```

## 10. 행동 결과에 연결 키 저장

PsychoPy 행동 데이터와 Neon 녹화를 연결하려면 모든 결과 파일에 다음 값을 넣는다.

```text
subject_id
session_id
neon_recording_id
```

`metadata.txt`와 각 행동 결과 파일에 `session_id`, `neon_recording_id`를 저장한다.

결과 저장 함수는 다음처럼 인자를 받게 만든다.

```python
save_results(
    save_directory,
    trial_results,
    session_id=session_id,
    neon_recording_id=neon_recording_id,
)
```

Excel에는 다음 열을 추가한다.

```text
session_id
neon_recording_id
```

이렇게 하면 나중에 다음 파일들을 하나의 session 단위로 합칠 수 있다.

```text
results_t.xlsx
frame_log.xlsx
trigger_timing_log.xlsx
neon_event_log.xlsx
Pupil Cloud exported gaze/AOI CSV
```

## 11. 다른 태스크에 적용하는 최소 순서

다른 PsychoPy 태스크에 Neon을 붙일 때는 다음 순서로 작업한다.

```text
1. utils/neon_client.py 같은 공통 client 모듈을 추가한다.
2. config.py에 USE_NEON, timeout, AprilTag 위치를 추가한다.
3. 참가자 시작 시 subject_id와 session_id를 만든다.
4. PsychoPy window 생성 후 AprilTagStim을 만들고 AutoDraw로 유지한다.
5. 첫 자극 전에 neon_client.start_session()으로 recording_id를 받는다.
6. 각 자극 onset frame에서 neon_client.call_on_flip()을 호출한다.
7. 분석하고 싶은 구간마다 SECTION_START / END를 paired event로 넣는다.
8. 응답, 오답, 무응답 이벤트를 실제 감지 시점에 enqueue한다.
9. Escape나 오류 시 열린 section을 닫고 EXPERIMENT_ABORT를 남긴다.
10. 종료 시 neon_client.close() 후 neon_event_log.xlsx를 저장한다.
11. 행동 결과와 metadata에 session_id, neon_recording_id를 저장한다.
```

## 12. 코드 작성 시 주의할 점

```text
자극 onset 이벤트를 일반 함수 호출로 바로 보내지 말고 callOnFlip에 등록한다.
flip callback 안에서 네트워크 전송을 직접 하지 않는다.
SECTION_START를 열었으면 반드시 SECTION_END로 닫는다.
응답 section은 응답 또는 timeout 시점에 닫는다.
USE_NEON=False에서도 같은 태스크 코드가 실행되도록 NullNeonClient를 둔다.
recording_id가 없으면 active recording이 아니므로 첫 자극 전에 중단한다.
실험 도중 returned recording_id가 바뀌면 성공으로 처리하지 않는다.
로그 저장은 정상 종료뿐 아니라 abort/finally 경로에서도 실행한다.
```

## 13. 권장 파일 배치

새 PsychoPy 실험에 붙일 때는 아래처럼 역할별 파일을 나눌 수 있다.

```text
config.py
  USE_NEON, Neon timeout, AprilTag 위치/크기

utils/neon_client.py
  NeonEventClient, NullNeonClient, section helper, event log 구조

main.py
  session 시작, AprilTag 생성, recording_id 저장, 종료 flush, 로그 저장

phase_func/run_trial.py
  trial 안의 STIMULUS/CHOICE/RESPONSE section 이벤트

save_func/save_results.py
  행동 결과에 session_id, neon_recording_id 저장
```

## 14. 요약

다른 PsychoPy 태스크에 Neon을 붙일 때 핵심은 코드상으로 다음 다섯 가지를 넣는 것이다.

```text
AprilTag
  PsychoPy window에 AprilTagStim을 만들고 AutoDraw로 실험 전체에 유지한다.

Neon event
  자극 onset은 win.callOnFlip()에서 timestamp를 잡아 queue에 넣는다.

SECTION_START / END
  Cloud에서 분석할 단위마다 section을 열고 닫는다.

neon_event_log.xlsx
  event queue, send success, retry, timestamp, recording_id를 로컬에 저장한다.

session_id + recording_id
  PsychoPy 결과 파일과 Pupil Cloud 녹화를 연결할 수 있게 모든 결과에 저장한다.
```

