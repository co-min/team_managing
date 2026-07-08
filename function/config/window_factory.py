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


class VisualObjectFactory:
    def __init__(self, win, animal_groups=None):
        self.win = win

        layout = self._compute_layout()
        av, ah, cy = layout['animal_v'], layout['animal_h'], layout['center_y']

        # 슬롯 위치: 상(0), 하(1), 우(2), 좌(3) — apply_layout에서 항상 덮어씀
        _slot_defaults = [(0, av + cy), (0, -av + cy), (ah, cy), (-ah, cy)]

        if animal_groups is not None:
            # CSV에서 읽은 그룹 정보로 동적으로 char_info 구성
            self.char_info = {}
            for group in animal_groups:
                for slot_idx, animal in enumerate(group):
                    self.char_info[animal] = {
                        'pos': _slot_defaults[slot_idx % 4],
                        'img': f'image/objectives/{animal}.png',
                    }
        else:
            # 폴백: 하드코딩된 24마리 6그룹 (하위 호환성 유지)
            self.char_info = {
                # Group 0
                'duck':    {'pos': _slot_defaults[0], 'img': 'image/objectives/duck.png'},
                'frog':    {'pos': _slot_defaults[1], 'img': 'image/objectives/frog.png'},
                'panda':   {'pos': _slot_defaults[2], 'img': 'image/objectives/panda.png'},
                'rabbit':  {'pos': _slot_defaults[3], 'img': 'image/objectives/rabbit.png'},
                # Group 1
                'bear':    {'pos': _slot_defaults[0], 'img': 'image/objectives/bear.png'},
                'cat':     {'pos': _slot_defaults[1], 'img': 'image/objectives/cat.png'},
                'chicken': {'pos': _slot_defaults[2], 'img': 'image/objectives/chicken.png'},
                'cow':     {'pos': _slot_defaults[3], 'img': 'image/objectives/cow.png'},
                # Group 2
                'horse':   {'pos': _slot_defaults[0], 'img': 'image/objectives/horse.png'},
                'koala':   {'pos': _slot_defaults[1], 'img': 'image/objectives/koala.png'},
                'lion':    {'pos': _slot_defaults[2], 'img': 'image/objectives/lion.png'},
                'tiger':   {'pos': _slot_defaults[3], 'img': 'image/objectives/tiger.png'},
                # Group 3
                'deer':     {'pos': _slot_defaults[0], 'img': 'image/objectives/deer.png'},
                'dog':      {'pos': _slot_defaults[1], 'img': 'image/objectives/dog.png'},
                'elephant': {'pos': _slot_defaults[2], 'img': 'image/objectives/elephant.png'},
                'fish':     {'pos': _slot_defaults[3], 'img': 'image/objectives/fish.png'},
                # Group 4
                'fox':   {'pos': _slot_defaults[0], 'img': 'image/objectives/fox.png'},
                'hippo': {'pos': _slot_defaults[1], 'img': 'image/objectives/hippo.png'},
                'kappa': {'pos': _slot_defaults[2], 'img': 'image/objectives/kappa.png'},
                'mouse': {'pos': _slot_defaults[3], 'img': 'image/objectives/mouse.png'},
                # Group 5
                'otter':   {'pos': _slot_defaults[0], 'img': 'image/objectives/otter.png'},
                'seal':    {'pos': _slot_defaults[1], 'img': 'image/objectives/seal.png'},
                'sealion': {'pos': _slot_defaults[2], 'img': 'image/objectives/sealion.png'},
                'sheep':   {'pos': _slot_defaults[3], 'img': 'image/objectives/sheep.png'},
            }

        self.char_list = list(animal_groups[0]) if animal_groups else ['duck', 'frog', 'panda', 'rabbit']

        # Slot positions: index 0=up, 1=down, 2=right, 3=left
        self._slot_positions = [(0, av + cy), (0, -av + cy), (ah, cy), (-ah, cy)]
        self.center_y = cy

        # Score block offsets (outer side of each animal, away from center)
        ov = layout['outer_v']
        self._slot_block_offsets = [(0, ov), (0, -ov), (0, ov), (0, ov)]
        self._block_size  = layout['block_size']
        self._animal_size = layout['animal_size']
        self._domain_size = layout['domain_size']
        self._domain_y    = layout['domain_y']

        self.domain_stim = None
        self.animal_stims = {}
        self.border_stims = {}
        self.block_stims = {}
        self.overlay_stims = {}
        self._locked_chars: set = set()

        self._create_ui_elements()

    def _compute_layout(self) -> dict:
        """win.size 기준으로 모든 레이아웃 수치를 비례 계산합니다."""
        W, H = self.win.size
        half_h = H // 2

        # 도메인 이미지 (상단, 정사각형)
        domain_size   = int(H * 0.155)
        domain_y      = half_h - domain_size // 2 - 20
        domain_bottom = domain_y - domain_size // 2

        # 동물 이미지 크기 및 십자 배치 거리
        animal_size = int(H * 0.148)
        animal_v    = int(H * 0.180)   # 중심으로부터 상하 거리
        animal_h    = int(W * 0.138)   # 중심으로부터 좌우 거리

        # 동물 십자 전체를 아래로 내려 도메인 질문과의 간격 확보
        center_y = -int(H * 0.09)

        # 상단 동물이 도메인 이미지 하단과 최소 25px 간격 유지 (center_y 반영)
        max_v    = domain_bottom - animal_size // 2 - 25 - center_y
        animal_v = min(animal_v, max_v)

        # 스코어 블록 크기
        block_h = int(H * 0.042)
        block_w = animal_size + 20

        # 스코어 블록: 동물 외곽(바깥쪽)에 배치, 도메인과 10px 이상 여백 유지
        outer_v     = animal_size // 2 + 10 + block_h // 2
        max_outer_v = domain_bottom - (animal_v + center_y) - block_h // 2 - 10
        outer_v     = min(outer_v, max_outer_v)

        return {
            'domain_size': domain_size,
            'domain_y':    domain_y,
            'animal_size': animal_size,
            'animal_v':    animal_v,
            'animal_h':    animal_h,
            'center_y':    center_y,
            'block_size':  (block_w, block_h),
            'outer_v':     outer_v,
        }

    def _create_ui_elements(self):
        """실험 시작 시 UI 요소들을 메모리에 고속 생성합니다."""
        ds = self._domain_size
        self.domain_stim = visual.ImageStim(
            win=self.win,
            pos=(0, self._domain_y),
            size=(ds, ds)
        )

        az = self._animal_size
        bz = az + 10   # 테두리는 동물 이미지보다 3px 크게
        for char_name, info in self.char_info.items():
            # part 2 백그라운드 블록 (apply_layout에서 위치/크기 재설정됨)
            self.block_stims[char_name] = visual.Rect(
                win=self.win,
                pos=info['pos'],
                width=az, height=az,
                fillColor= None,
                lineColor=None,
                opacity=0,
                units='pix'
            )

            # 기본 동물 이미지 캐릭터
            self.animal_stims[char_name] = visual.ImageStim(
                win=self.win,
                image=info['img'],
                pos=info['pos'],
                size=(az, az),
                units='pix'
            )

            # part 1 하이라이트 테두리
            self.border_stims[char_name] = visual.Rect(
                win=self.win,
                pos=info['pos'],
                width=bz, height=bz,
                lineWidth=12,
                lineColor= None,
                fillColor=None,
                units='pix'
            )

            # part 2 어두운 반투명 오버레이
            self.overlay_stims[char_name] = visual.Rect(
                win=self.win,
                pos=info['pos'],
                width=az, height=az,
                fillColor='black',
                lineColor=None,
                opacity=0.5,
                units='pix'
            )

    def update_domain(self, domain_name):
        """시행(Trial) 시작 시 상단 도메인 질문 이미지(cooking, repairing, tennis)를 바꿉니다."""
        img_path = f"image/domains/{domain_name}.png"
        self.domain_stim.setImage(img_path)

    def reset_ui_states(self):
        """매 Trial 시작 전 모든 테두리와 블록 색상을 초기 상태로 깨끗하게 청소합니다."""
        self._locked_chars.clear()
        for char_name in self.char_list:
            self.border_stims[char_name].setLineColor('white')
            self.border_stims[char_name].lineWidth = 6
            self.border_stims[char_name].opacity = 0
            self.block_stims[char_name].setFillColor('white')
            self.block_stims[char_name].opacity = 0

    def set_animal_locked(self, char_name: str, locked: bool) -> None:
        """Choice 1 확정 시 동물 이미지 위에 OVERLAY를 activate/disactivate 합니다."""
        if locked:
            self._locked_chars.add(char_name)
        else:
            self._locked_chars.discard(char_name)

    def apply_layout(self, char_order: list) -> None:
        """
        Rearrange which animal appears at each spatial slot for this trial.

        char_order : list of 4 animal names, e.g. ['rabbit', 'duck', 'panda', 'frog']
                     Index 0 = up-arrow slot, 1 = down, 2 = right, 3 = left.
        """
        for slot_idx, (animal_name, pos) in enumerate(zip(char_order, self._slot_positions)):
            self.animal_stims[animal_name].setPos(pos)
            self.border_stims[animal_name].setPos(pos)
            self.overlay_stims[animal_name].setPos(pos)

            dx, dy = self._slot_block_offsets[slot_idx]
            block_pos = (pos[0] + dx, pos[1] + dy)
            self.block_stims[animal_name].setPos(block_pos)
            self.block_stims[animal_name].setSize(self._block_size)

        self.char_list = list(char_order)

    def draw_base_scene(self, phase_type='phase1'):
        """
        DOMAIN QUESTION과 ANIMALS를 순서대로 RENDERING합니다.
        """
        self.domain_stim.draw()

        show_blocks = phase_type == 'phase2'
        for char_name in self.char_list:
            if show_blocks:
                self.block_stims[char_name].draw()
            self.animal_stims[char_name].draw()
            if char_name in self._locked_chars:
                self.overlay_stims[char_name].draw()
            self.border_stims[char_name].draw()


# ── Shared singleton ──────────────────────────────────────────────────────────
_shared_factory: 'VisualObjectFactory | None' = None


def get_shared_factory(win: visual.Window, animal_groups=None) -> VisualObjectFactory:
    """Return (or lazily create) the one shared VisualObjectFactory per window.

    animal_groups : list of lists returned by load_all_data().
                    Pass on the first call (from main) to build the factory
                    from the actual CSV groups. Subsequent calls (from phases)
                    omit it and receive the already-initialised instance.
    """
    global _shared_factory
    if _shared_factory is None:
        _shared_factory = VisualObjectFactory(win, animal_groups)
    return _shared_factory