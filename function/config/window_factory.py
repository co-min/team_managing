"""
window_factory.py
-----------------
Creates and returns a configured PsychoPy Window.
Keeping window creation isolated makes it easy to swap
monitor profiles or resolution without touching phase logic.
"""

from psychopy import visual, monitors
from function.config.settings import (
    WINDOW_SIZE, WINDOW_UNITS, WINDOW_FULLSCR,
    BACKGROUND_COLOR, MONITOR_NAME, SCREEN_NUMBER,
)


def create_window() -> visual.Window:
    """
    Build and return the experiment Window.

    Returns
    -------
    visual.Window
        A fully initialised PsychoPy window ready for drawing.
    """
    mon = monitors.Monitor(MONITOR_NAME)
    # TODO: set mon.setSizePix(), mon.setWidth(), mon.setDistance()
    #       to match your physical setup for correct visual-angle scaling.

    win = visual.Window(
        size=WINDOW_SIZE,
        fullscr=WINDOW_FULLSCR,
        units=WINDOW_UNITS,
        monitor=mon,
        color=BACKGROUND_COLOR,
        colorSpace="hex",
        allowGUI=True,
        winType="pyglet",
        screen=SCREEN_NUMBER,
    )
    return win

from psychopy import visual

class VisualObjectFactory:
    def __init__(self, win):
        """
        실험에 필요한 모든 시각적 객체(윈도우, 도메인 이미지, 동물 캐릭터, 키보드 포커스 UI)를 
        생성하고 관리하는 팩토리 클래스입니다.
        """
        self.win = win
        
        # 1. 캐릭터 정보 및 십자형(Cross) 배치 좌표 설정 (화면 중심 기준 픽셀 단위)
        # 상(Duck), 하(Frog), 우(Panda), 좌(Rabbit)  — 화살표 방향과 일치
        self.char_info = {
            'duck':   {'pos': (   0,  250), 'img': 'image/objectives/duck.png'},
            'frog':   {'pos': (   0, -250), 'img': 'image/objectives/frog.png'},
            'panda':  {'pos': ( 250,    0), 'img': 'image/objectives/panda.png'},
            'rabbit': {'pos': (-250,    0), 'img': 'image/objectives/rabbit.png'}
        }
        
        # 키보드 인덱스 매핑용 리스트 (순서 고정)
        self.char_list = ['duck', 'frog', 'panda', 'rabbit']
        
        # 2. 시각 컴포넌트 초기화
        self.domain_stim = None
        self.animal_stims = {}
        self.border_stims = {}
        self.block_stims = {}
        
        self._create_ui_elements()

    def _create_ui_elements(self):
        """실험 시작 시 UI 요소들을 메모리에 고속 생성합니다."""
        
        # A. 상단 도메인 이미지 Stimulus 공간 확보 (main에서 경로 동적 업데이트)
        self.domain_stim = visual.ImageStim(
            win=self.win,
            pos=(0, 540),
            size=(250, 250)
        )
        
        # B. 4마리 동물 캐릭터 및 개별 테두리/블록 세트 생성
        for char_name, info in self.char_info.items():
            # 파트 2용 백그라운드 블록 (이미지 뒤에 배치되어 색상이 변하는 영역)
            self.block_stims[char_name] = visual.Rect(
                win=self.win,
                pos=info['pos'],
                width=240,
                height=240,
                fillColor='white',
                lineColor=None,
                units='pix'
            )
            
            # 기본 동물 이미지 캐릭터
            self.animal_stims[char_name] = visual.ImageStim(
                win=self.win,
                image=info['img'],
                pos=info['pos'],
                size=(180, 180),
                units='pix'
            )
            
            # 파트 1용 하이라이트 테두리 (기본값은 투명 또는 흰색)
            self.border_stims[char_name] = visual.Rect(
                win=self.win,
                pos=info['pos'],
                width=200,
                height=200,
                lineWidth=3,
                lineColor='whit e',
                fillColor=None,
                units='pix'
            )

    def update_domain(self, domain_name):
        """시행(Trial) 시작 시 상단 도메인 질문 이미지(cooking, repairing, tennis)를 바꿉니다."""
        img_path = f"image/domains/{domain_name}.png"
        self.domain_stim.setImage(img_path)

    def reset_ui_states(self):
        """매 Trial 시작 전 모든 테두리와 블록 색상을 초기 상태로 깨끗하게 청소합니다."""
        for char_name in self.char_list:
            self.border_stims[char_name].setLineColor('white')
            self.block_stims[char_name].setFillColor('white')

    # Slot positions: index 0=up, 1=down, 2=right, 3=left  (matches ArrowKeyboard order)
    _SLOT_POSITIONS = [(0, 250), (0, -250), (250, 0), (-250, 0)]

    def apply_layout(self, char_order: list) -> None:
        """
        Rearrange which animal appears at each spatial slot for this trial.

        char_order : list of 4 animal names, e.g. ['rabbit', 'duck', 'panda', 'frog']
                     Index 0 = up-arrow slot, 1 = down, 2 = right, 3 = left.
        """
        for animal_name, pos in zip(char_order, self._SLOT_POSITIONS):
            self.animal_stims[animal_name].setPos(pos)
            self.border_stims[animal_name].setPos(pos)
            self.block_stims[animal_name].setPos(pos)
        self.char_list = list(char_order)

    def draw_base_scene(self, phase_type='phase1'):
        """
        화면에 기본적인 실험 배경을 그립니다.
        상단 도메인 퀘스천과 4마리 동물 캐릭터를 순서대로 렌더링합니다.
        """
        self.domain_stim.draw()

        for char_name in self.char_list:
            # 파트 2(시너지)일 때는 점수에 따라 바뀌는 컬러 블록 배경을 먼저 그립니다
            if phase_type == 'phase2':
                self.block_stims[char_name].draw()

            self.animal_stims[char_name].draw()

            # 파트 1(역량)일 때는 텍스처 위에 하이라이트 테두리를 덮어 그립니다
            if phase_type == 'phase1':
                self.border_stims[char_name].draw()


# ── Shared singleton ──────────────────────────────────────────────────────────
_shared_factory: 'VisualObjectFactory | None' = None


def get_shared_factory(win: visual.Window) -> VisualObjectFactory:
    """Return (or lazily create) the one shared VisualObjectFactory per window."""
    global _shared_factory
    if _shared_factory is None:
        _shared_factory = VisualObjectFactory(win)
    return _shared_factory