# V2.5 / V2.6 → V2.6.1 Migration

V2.6.1은 `index.html`의 JavaScript 엔진을 사용하지 않고 `app.py + core/` Python 엔진으로 실행합니다.

## GitHub에서 교체

저장소 루트의 실행 파일을 이 패키지 기준으로 교체합니다.

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

### 선택
- `sample_data/` — 테스트 파일일 뿐이며 앱 시작 시 자동으로 불러오지 않습니다.
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

실행하면 샘플 화면이 아니라 빈 `데이터` 화면에서 시작합니다.
