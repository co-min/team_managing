import os
import pandas as pd
from psychopy import logging

class DataLoader:
    def __init__(self):
        """
        실험에 필요한 3개의 CSV 데이터를 로드하고 
        키보드 실시간 탐색에 최적화된 딕셔너리 구조로 변환합니다.
        """
        # 파일 경로 설정 (기본 stimuli/ 폴더 기준)
        self.stimuli_dir = "stimuli"
        
        # 1. CSV 파일 로드
        self.comp_df = self._load_csv("competence_table.csv")
        self.syn_df = self._load_csv("synergy_table.csv")
        self.score_df = self._load_csv("score_table.csv")
        
        # 2. 실시간 조회를 위한 딕셔너리 캐싱 (딕셔너리 변환)
        self.competence_cache = {}
        self.synergy_cache = {}
        self.score_cache = {}
        
        self._build_caches()

    def _load_csv(self, file_name):
        """CSV 파일을 안전하게 로드합니다."""
        path = os.path.join(self.stimuli_dir, file_name)
        if not os.path.exists(path):
            # 개발 및 테스트 단계에서 파일 위치 오류 방지
            path = file_name 
            if not os.path.exists(path):
                raise FileNotFoundError(f"필수 자극 파일이 없습니다: {file_name}")
        return pd.read_csv(path)

    def _build_caches(self):
        """
        방향키가 움직일 때마다 실시간 초고속 조회가 가능하도록 
        (char1, char2) 튜플을 키로 갖는 딕셔너리를 빌드합니다.
        """
        # A. Competence Table 캐싱 (도메인별 점수 분리 저장)
        # 컬럼 구조: pair_id, char1, char2, sc_cooking, sc_repairing, sc_tennis
        for _, row in self.comp_df.iterrows():
            c1, c2 = str(row['char1']).strip(), str(row['char2']).strip()
            # 사용자가 캐릭터를 어떤 순서로 탐색하든 매칭되도록 양방향 정렬 정규화
            key = tuple(sorted([c1, c2])) 
            
            self.competence_cache[key] = {
                'cooking': int(row['sc_cooking']),
                'repairing': int(row['sc_repairing']),
                'tennis': int(row['sc_tennis'])
            }

        # B. Synergy Table 캐싱
        # 컬럼 구조: pair_id, char1, char2, synergy_score
        for _, row in self.syn_df.iterrows():
            c1, c2 = str(row['char1']).strip(), str(row['char2']).strip()
            key = tuple(sorted([c1, c2]))
            self.synergy_cache[key] = int(row['synergy_score'])

        # C. Score Table 캐싱 (최종 게이지 피드백용 점수판)
        # score_table.csv 구조가 competence 혹은 별도 기준이더라도 도메인별 매핑 대응
        # 만약 score_table이 competence_table과 구조가 같다면 아래처럼 파싱합니다.
        for _, row in self.score_df.iterrows():
            c1, c2 = str(row['char1']).strip(), str(row['char2']).strip()
            key = tuple(sorted([c1, c2]))
            
            # 도메인 컬럼 범용 처리 (sc_cooking 또는 cooking 형태 둘 다 대응)
            self.score_cache[key] = {}
            for col in self.score_df.columns:
                if 'cooking' in col.lower():
                    self.score_cache[key]['cooking'] = int(row[col])
                elif 'repairing' in col.lower():
                    self.score_cache[key]['repairing'] = int(row[col])
                elif 'tennis' in col.lower():
                    self.score_cache[key]['tennis'] = int(row[col])

    def get_competence_score(self, char1, char2, domain):
        """
        [파트 1용] 두 동물과 현재 도메인을 입력받아 역량 점수(3, 2, 1)를 반환합니다.
        테두리 색상 분기에 사용됩니다. (3: Green, 2: Yellow, 1: Red)
        """
        key = tuple(sorted([str(char1), str(char2)]))
        domain_key = str(domain).lower().replace('sc_', '') # 'sc_cooking' 입력 시 'cooking'으로 변환
        
        domain_dict = self.competence_cache.get(key)
        if domain_dict and domain_key in domain_dict:
            return domain_dict[domain_key]
        
        logging.warning(f"Competence 점수를 찾을 수 없습니다: {char1}-{char2} 인덱스 확인 필요")
        return 2 # 예외 발생 시 기본값(Yellow에 대응하는 2점) 반환

    def get_synergy_score(self, char1, char2):
        """
        [파트 2용] 두 동물 간의 시너지 점수(1, 0, -1)를 반환합니다.
        방향키 조작 시 블록 색상 분기에 사용됩니다. (1: Green, 0: Yellow, -1: Red)
        """
        key = tuple(sorted([str(char1), str(char2)]))
        if key in self.synergy_cache:
            return self.synergy_cache[key]
        
        logging.warning(f"Synergy 점수를 찾을 수 없습니다: {char1}-{char2} 인덱스 확인 필요")
        return 0 # 예외 발생 시 기본값(Yellow에 대응하는 0점) 반환

    def get_feedback_score(self, char1, char2, domain):
        """
        [공통 피드백용] 최종 선택된 조합의 게이지 피드백 점수(-3 ~ +3)를 반환합니다.
        """
        key = tuple(sorted([str(char1), str(char2)]))
        domain_key = str(domain).lower().replace('sc_', '')
        
        domain_dict = self.score_cache.get(key)
        if domain_dict and domain_key in domain_dict:
            return domain_dict[domain_key]
        
        logging.warning(f"Feedback 점수를 찾을 수 없습니다: {char1}-{char2} 인덱스 확인 필요")
        return 0 # 예외 발생 시 기본값(0점, Intermediate 위치) 반환