# FinSight AI

> 재무제표 이상징후 탐지 + 전표 분류를 한 곳에서 처리하는 **Python 기반 재무 분석 워크스페이스**

FinSight AI는 재무·회계 담당자가 반복적으로 하는 **증감 비교, 이상 계정 확인, 원본 대조, 전표 분류** 작업을 줄이기 위한 도구입니다.

## V2.6.1 핵심 변경

V2.6부터 **계산·검증·이상징후 탐지·추세 분석·전표 추천 엔진을 JavaScript에서 Python으로 이전**했습니다. V2.6.1은 업무 흐름과 가독성을 복구하고, 실행 시 샘플 없이 빈 프로젝트로 시작하도록 정리한 버전입니다.

```text
파일 업로드
   ↓
Python Parser
   ↓
pandas DataFrame
   ↓
Validation Engine
   ↓
Anomaly / Trend Engine
   ↓
Streamlit UI
```

브라우저 UI가 숫자를 계산하는 구조가 아니라 서버의 Python 엔진이 결과를 생성합니다.


## 시작 화면

프로그램을 실행하면 샘플 재무제표나 샘플 전표가 자동으로 채워지지 않습니다. **빈 데이터 화면에서 사용자가 파일을 불러오는 순간부터 작업이 시작**됩니다.

- 재무 데이터 검색 / 재무제표 필터 / 변경 행만 보기
- 이상징후에서 해당 데이터로 바로 이동
- 미검토 우선 정렬
- PDF/DOCX 원본 대조 전 `임시 결과` 표시
- 전표 검색 / 상태 / 중복 / 미분류 필터

## 주요 기능

- Excel / CSV / PDF / DOCX 재무데이터 가져오기
- 전기·당기·계정과목·단위 매핑 확인
- 재무데이터 직접 수정 후 재분석
- 자산 = 부채 + 자본 등 기본 검증
- 전기 대비 변동 / 중요성 / 연관계정 신호 분석
- 3개 이상 기간의 추세 이탈 분석
- 원본 파일·시트·셀·페이지 추적
- 검토 메모 / 완료 상태 관리
- Excel / CSV 전표 일괄 가져오기
- 과거 승인 기억 + 키워드 기반 계정 추천
- 중복 의심 전표 탐지
- 프로젝트 JSON 백업 / 복원
- 결과 CSV 내보내기

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud

```text
Repository: jjiwooking/FinSight-AI
Branch: main
Main file path: app.py
```

## Project Structure

```text
FinSight-AI/
├── app.py
├── core/
│   ├── anomaly.py
│   ├── io.py
│   ├── project.py
│   ├── sample.py
│   ├── transactions.py
│   ├── trend.py
│   ├── utils.py
│   └── validation.py
├── tests/
│   └── test_engine.py
├── sample_data/
├── legacy/
│   └── index_v2_5.html
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── CHANGELOG.md
└── VERSION
```

## 분석 원칙

**AI가 회계 결론을 대신 내리는 도구가 아니라, 사람이 확인해야 할 항목을 줄이는 도구**를 목표로 합니다.

- 계산과 검증은 Python 규칙 엔진이 수행합니다.
- 원인이 확정되지 않은 이상징후는 단정하지 않습니다.
- 추천 점수는 회계 위험 확률이나 통계적 확률이 아닙니다.
- PDF / DOCX 추출값은 원본 대조 전까지 확인 필요 상태로 취급합니다.
- 최종 회계 판단은 사용자에게 있습니다.

## 현재 한계

- PDF/DOCX는 텍스트 추출 기반이며 복잡한 표/OCR 정확도에는 한계가 있습니다.
- 전표 추천은 아직 ML/LLM 분류 모델이 아니라 승인 기억 + 명시적 규칙 기반입니다.
- 서버 DB, 로그인, 조직 권한 기능은 아직 없습니다.
- 우선순위 점수는 검증된 감사 위험 확률이 아닙니다.

## Goal

**10분 걸리던 확인 작업을 1~2분으로 줄이는 것.**

기능 수보다 **적은 클릭, 빠른 이해, 쉬운 수정과 재검토**를 우선합니다.
