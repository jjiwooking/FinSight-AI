# V2.5 / V2.6 → V2.6.2 Migration

V2.6.2는 `index.html`의 JavaScript 엔진을 사용하지 않고 `app.py + core/` Python 엔진으로 실행합니다.

## GitHub에서 교체

저장소 루트에 이 패키지의 파일과 폴더를 그대로 덮어씁니다.

### 반드시 업로드
- `app.py`
- `core/` 전체
- `requirements.txt`
- `.streamlit/config.toml`
- `.gitignore`
- `README.md`
- `CHANGELOG.md`
- `VERSION`

### 권장
- `tests/`
- `pytest.ini`
- `requirements-dev.txt`
- `sample_data/` — 정상/이상징후/오류/전표 검증용 합성 파일

### 선택
- `legacy/` — 과거 V2.5 코드 보관용이며 실행에는 필요하지 않습니다.

### 올리지 않기
- `__pycache__/`
- `.pytest_cache/`
- `.venv/`, `venv/`
- `.env`, API Key, 비밀번호
- 실제 회사 재무데이터 / 실제 전표
- 프로젝트 JSON 백업 / 결과 CSV

## Streamlit 설정
- Repository: `jjiwooking/FinSight-AI`
- Branch: `main`
- Main file: `app.py`

## V2.6.2 금액 기준
- 내부 저장/계산/편집: 원(KRW)
- 원본 단위: 원 / 천원 / 백만원 / 억원 선택 후 원으로 환산
- 화면 편집 숫자: `1,000,000` 형태의 천 단위 쉼표
- 분석 표시 단위: 원 / 천원 / 백만원 / 억원 선택 가능
- CSV 내보내기: 항상 원(KRW) 원값

실행하면 예시 데이터가 자동으로 들어가지 않고 빈 `데이터` 화면에서 시작합니다.
