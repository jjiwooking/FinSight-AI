# FinSight AI

**재무제표 이상징후 탐지 + 전표 분류 워크스페이스**

FinSight AI V2.5를 **GitHub 저장소에 그대로 올리고 Streamlit Community Cloud에서 `app.py`로 배포할 수 있도록 패키징한 버전**입니다.

## 핵심 구조

```text
FinSight-AI/
├─ app.py                         # Streamlit 배포 엔트리포인트
├─ index.html                     # FinSight AI V2.5 본체
├─ requirements.txt
├─ .streamlit/
│  └─ config.toml
├─ sample_data/
│  ├─ sample_financial_4year.csv
│  └─ sample_transactions.csv
├─ CHANGELOG.md
├─ README.md
└─ .gitignore
```

## 로컬 실행

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

브라우저가 자동으로 열리지 않으면 터미널에 표시되는 로컬 주소로 접속합니다.

## GitHub에 올리기

이 폴더의 **내용 전체를 `jjiwooking/FinSight-AI` 저장소 루트**에 올리면 됩니다.

권장 루트 파일은 `app.py`, `index.html`, `requirements.txt`, `README.md`입니다.

> 실제 회사 재무제표, 전표, 개인정보, 계좌정보 등 민감한 데이터는 public GitHub 저장소에 커밋하지 마세요. `sample_data/`에는 테스트용 가상 데이터만 둡니다.

## Streamlit Community Cloud 배포

1. Streamlit Community Cloud에서 **Create app** 선택
2. Repository: `jjiwooking/FinSight-AI`
3. Branch: `main`
4. Main file path: `app.py`
5. Deploy

별도 Python 데이터 처리 라이브러리는 필요하지 않습니다. 현재 V2.5의 재무/전표 파일 처리는 기존 HTML/JavaScript 엔진이 브라우저 안에서 수행합니다.

## 현재 배포 구조의 장점

- 기존 V2.5 UI와 기능을 거의 그대로 유지
- Streamlit용으로 전면 재작성하지 않아 기능 손실 위험이 낮음
- GitHub Pages에서는 `index.html`을 직접 사용할 수도 있음
- Streamlit에서는 `app.py`가 V2.5를 임베드해 서비스
- 사용자가 UI 내부에서 선택한 Excel/CSV/PDF/DOCX 파일은 기존 브라우저 파서가 처리

## 주의사항

- XLSX / PDF / DOCX 파서가 jsDelivr CDN을 통해 로드되므로 해당 형식 사용 시 인터넷 연결이 필요합니다.
- PDF/DOCX 추출은 production 수준 OCR/레이아웃 인식 엔진이 아닙니다.
- 전표 추천 점수는 확률이 아니라 검토 우선순위용 상대 점수입니다.
- AI가 K-IFRS 판단이나 최종 계정과목을 자동 확정하지 않습니다.
- 브라우저 저장은 사용자가 직접 켜는 opt-in 구조입니다.
- `components.html` 기반이므로 FinSight UI는 Streamlit 페이지 안의 iframe에서 실행됩니다.

## 다음 아키텍처 단계

이 패키지는 **V2.5 기능을 손상시키지 않고 즉시 배포하기 위한 브리지 버전**입니다. 실제 운영형으로 발전시킬 때는 아래를 Python/backend로 순차 이전하는 것이 적절합니다.

- 파일 파싱과 데이터 검증
- 프로젝트 저장/버전 관리
- 회사별 계정과목표(CoA)
- 과거 승인 전표 학습 데이터
- 조직/사용자 인증과 권한
- 서버 기반 분석 API

FinSight의 기준은 기능 수가 아니라 **실제 회계·재무 업무에서 반복 확인과 수작업을 얼마나 줄이는가**입니다.
