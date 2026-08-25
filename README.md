# FinSight AI

> 재무제표 이상징후 탐지 + 전표 분류를 한 곳에서 처리하는 재무 분석 워크스페이스

FinSight AI는 재무·회계 담당자가 반복적으로 하는  
**증감 비교, 이상 계정 확인, 원본 대조, 전표 분류 작업을 줄이기 위한 도구**입니다.

---

## ✨ What it does

### 📊 재무제표 이상징후 탐지
- 전기 / 당기 증감 자동 비교
- 급격한 변동 계정 탐지
- 매출채권·재고·현금흐름 등 관련 계정 함께 확인
- 검토 우선순위 자동 정리

### 📈 다기간 추세 분석
3개 이상의 기간이 있으면  
최근 변화를 과거 패턴과 비교해 **추세 이탈 계정**을 찾아줍니다.

### 🧾 전표 분류
- Excel / CSV 전표 일괄 업로드
- 일자 / 적요 / 금액 자동 매핑
- 과거 승인 이력 및 키워드 기반 계정 추천
- 승인 / 반려 / 최종 계정 수정

### 🔎 원본 추적
분석 결과에서 사용된 숫자의

- 파일
- 시트
- 행
- 셀
- PDF 페이지

위치를 함께 확인할 수 있습니다.

---

## 🚀 Workflow

```text
데이터 업로드
      ↓
자동 매핑 확인
      ↓
데이터 검증
      ↓
이상징후 탐지
      ↓
원본 확인 / 수정
      ↓
재분석
      ↓
검토 결과 내보내기
```

---

## 🛠 Supported Files

### 재무데이터

```text
.xlsx
.xls
.csv
.pdf
.docx
```

### 전표데이터

```text
.xlsx
.xls
.csv
```

---

## ▶ Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## ☁ Streamlit Deploy

Streamlit Community Cloud에서:

```text
Repository
jjiwooking/FinSight-AI

Branch
main

Main file
app.py
```

---

## 📁 Project Structure

```text
FinSight-AI/
├── app.py
├── index.html
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── VERSION
│
├── .streamlit/
│   └── config.toml
│
└── sample_data/
    ├── sample_financial_4year.csv
    └── sample_transactions.csv
```

---

## 🧠 Analysis Principle

FinSight AI는 AI가 회계 판단을 대신하도록 만들지 않았습니다.

숫자 계산과 이상징후 탐지는 규칙 기반으로 처리하고,  
사용자가 **왜 이 항목을 확인해야 하는지** 빠르게 파악할 수 있도록 돕습니다.

```text
AI가 결론을 내리는 도구 ❌

확인해야 할 항목을 줄여주는 도구 ✅
```

---

## ⚠ Current Limitations

현재 **V2.5 Prototype**입니다.

- PDF / DOCX 표 추출 정확도 제한
- OCR 미지원
- 전표 추천은 아직 실제 ML 모델이 아닌 규칙 + 승인 이력 기반
- 서버 DB / 로그인 / 조직 권한 기능 없음
- 검토 우선순위 점수는 감사 위험 확률이 아님

---

## 🗺 Roadmap

- 회사별 계정과목표(CoA) 업로드
- 과거 전표 기반 추천 고도화
- 월 / 분기 / 다년 추세 분석
- 보고서 자동 생성
- 사용자 로그인 / 프로젝트 저장
- OCR 및 문서 구조 인식
- AI 설명 엔진 연결

---

## 🎯 Goal

**10분 걸리던 재무 확인 작업을 1~2분으로 줄이는 것.**

기능을 많이 넣는 것보다  
**더 적게 클릭하고, 더 빨리 이해하고, 바로 수정할 수 있는 것**을 우선합니다.
