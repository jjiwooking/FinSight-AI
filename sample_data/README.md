# FinSight AI 검증용 예시 파일

이 폴더의 데이터는 모두 합성 데이터이며 실제 회사 정보가 아닙니다. 모든 금액은 **원(KRW)** 단위입니다.

- `sample_financial_valid_4year.xlsx`: 재무상태표 등식과 현금흐름 연결이 맞는 정상 데이터
- `sample_financial_anomaly_4year.xlsx`: 등식은 맞지만 매출채권, 접대비, 기타영업비용, 영업활동현금흐름 등에 명확한 검토 신호가 있는 데이터
- `sample_financial_validation_errors.xlsx`: 중복 계정, 빈 금액, 재무상태표 등식 불일치, 현금흐름 연결 불일치를 의도적으로 포함한 데이터
- `sample_transactions_validation.xlsx`: 추천 가능 전표, 중복 전표, 음수 환불, 미분류 전표를 포함한 전표 검증 데이터

금액 셀은 Excel에서 `1,000,000`, 음수는 `(125,000)`, 0은 `-`로 보이도록 표시되어 있습니다.
