from __future__ import annotations

import pandas as pd

from .transactions import mark_duplicates


def financial_sample() -> pd.DataFrame:
    base = [
        ("매출액", "손익계산서", 2_850_000_000, 3_210_000_000, [2_460_000_000, 2_660_000_000, 2_850_000_000, 3_210_000_000]),
        ("영업이익", "손익계산서", 420_000_000, 310_000_000, [360_000_000, 395_000_000, 420_000_000, 310_000_000]),
        ("당기순이익", "손익계산서", 290_000_000, 238_000_000, [250_000_000, 271_000_000, 290_000_000, 238_000_000]),
        ("접대비", "손익계산서", 12_000_000, 45_600_000, [10_500_000, 11_800_000, 12_000_000, 45_600_000]),
        ("기타영업비용", "손익계산서", 5_000_000, 42_000_000, [4_300_000, 4_700_000, 5_000_000, 42_000_000]),
        ("광고선전비", "손익계산서", 18_000_000, 3_600_000, [15_000_000, 16_500_000, 18_000_000, 3_600_000]),
        ("종업원급여", "손익계산서", 240_000_000, 316_000_000, [210_000_000, 225_000_000, 240_000_000, 316_000_000]),
        ("매출채권", "재무상태표", 380_000_000, 610_000_000, [315_000_000, 345_000_000, 380_000_000, 610_000_000]),
        ("재고자산", "재무상태표", 290_000_000, 352_000_000, [255_000_000, 272_000_000, 290_000_000, 352_000_000]),
        ("자산총계", "재무상태표", 2_400_000_000, 2_700_000_000, [2_180_000_000, 2_290_000_000, 2_400_000_000, 2_700_000_000]),
        ("부채총계", "재무상태표", 1_400_000_000, 1_550_000_000, [1_280_000_000, 1_340_000_000, 1_400_000_000, 1_550_000_000]),
        ("자본총계", "재무상태표", 1_000_000_000, 1_150_000_000, [900_000_000, 950_000_000, 1_000_000_000, 1_150_000_000]),
        ("영업활동현금흐름", "현금흐름표", 95_000_000, 23_000_000, [82_000_000, 91_000_000, 95_000_000, 23_000_000]),
    ]
    rows = []
    for i, (account, statement, prior, current, values) in enumerate(base, start=1):
        rows.append(
            {
                "id": i,
                "account": account,
                "statement": statement,
                "prior": prior,
                "current": current,
                "included": True,
                "series": dict(zip(["2022", "2023", "2024", "2025"], values)),
                "source_file": "샘플 데이터",
                "source_sheet": statement,
                "source_row": i + 1,
                "source_page": None,
                "prior_cell": "샘플",
                "current_cell": "샘플",
                "period_cells": {},
                "unit": "원",
                "multiplier": 1,
                "method": "sample",
                "mapping_confirmed": True,
                "value_confirmed": True,
                "user_adjusted": False,
            }
        )
    return pd.DataFrame(rows)


def transaction_sample() -> pd.DataFrame:
    rows = [
        {"id": 1, "date": "08/01", "desc": "스타벅스 강남점", "amount": 23000, "original_account": "", "ai_account": "복리후생비", "recommendation_score": 72, "recommendation_source": "식음료 키워드", "final_account": "복리후생비", "status": "대기", "user_modified": False, "duplicate": False, "source_file": "샘플 전표", "source_row": 2},
        {"id": 2, "date": "08/02", "desc": "AWS", "amount": 420000, "original_account": "", "ai_account": "전산비", "recommendation_score": 78, "recommendation_source": "클라우드 키워드", "final_account": "전산비", "status": "대기", "user_modified": False, "duplicate": False, "source_file": "샘플 전표", "source_row": 3},
        {"id": 3, "date": "08/02", "desc": "카카오택시", "amount": 18200, "original_account": "", "ai_account": "여비교통비", "recommendation_score": 86, "recommendation_source": "교통 키워드", "final_account": "여비교통비", "status": "승인", "user_modified": False, "duplicate": False, "source_file": "샘플 전표", "source_row": 4},
    ]
    return mark_duplicates(pd.DataFrame(rows))
