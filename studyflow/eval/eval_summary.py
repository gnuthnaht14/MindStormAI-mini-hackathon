from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dotenv import load_dotenv  # noqa: E402
from google import genai  # noqa: E402
from google.genai import types as genai_types  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from studyflow.config import AppSettings  # noqa: E402
from studyflow.services import generate_study_material  # noqa: E402
from studyflow.services.pdf_service import extract_pdf_text  # noqa: E402

# ---------------------------------------------------------------------------
# Nối vào agent thật (theo app.py): generate_study_material() gọi OpenRouter,
# trong 1 lần AI call tạo cả summary + quiz. Ở đây chỉ lấy phần .summary ra
# để chấm điểm tóm tắt. question_count/question_types chỉ ảnh hưởng phần quiz,
# không ảnh hưởng chất lượng summary, nên để cố định cho mọi lần chạy eval.
# ---------------------------------------------------------------------------
_SETTINGS: AppSettings | None = None


def _get_settings() -> AppSettings:
    global _SETTINGS
    if _SETTINGS is None:
        load_dotenv(PROJECT_ROOT / ".env")
        _SETTINGS = AppSettings.from_env()
    return _SETTINGS


def summarize_document(document_text: str) -> str:
    settings = _get_settings()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Thiếu OPENROUTER_API_KEY trong .env")
    material = generate_study_material(
        document_text,
        question_count=8,
        question_types=["multiple_choice", "short_answer"],
        api_key=api_key,
        model=settings.openrouter_model,
    )
    return material.summary


# ---------------------------------------------------------------------------
# TIÊU CHÍ ĐÁNH GIÁ — mỗi tiêu chí được judge chấm riêng 1-5 sao, sau đó code
# tự tính % tổng theo trọng số (không để LLM tự cộng điểm, tránh sai số học).
# Đổi trọng số ở đây nếu muốn nhấn mạnh tiêu chí nào hơn.
# ---------------------------------------------------------------------------
CRITERIA: dict[str, dict[str, Any]] = {
    "faithfulness": {
        "weight": 0.40,
        "label": "Độ trung thực (không bịa)",
        "prompt": "Bản tóm tắt có bịa thêm thông tin, số liệu, hay suy diễn ngoài những gì tài liệu gốc nói không? 5 = hoàn toàn trung thực, không có gì bịa; 1 = có nhiều nội dung bịa/sai lệch nghiêm trọng.",
    },
    "coverage": {
        "weight": 0.30,
        "label": "Độ bao quát ý chính",
        "prompt": "Bản tóm tắt có nêu đủ các ý CHÍNH, quan trọng nhất của tài liệu gốc không? 5 = đầy đủ ý chính; 1 = thiếu gần hết ý chính.",
    },
    "conciseness": {
        "weight": 0.15,
        "label": "Độ súc tích",
        "prompt": "Bản tóm tắt có súc tích, không lan man, không lặp ý, không chứa chi tiết phụ không cần thiết không? 5 = rất súc tích; 1 = dài dòng/thừa nhiều.",
    },
    "coherence": {
        "weight": 0.15,
        "label": "Mạch lạc / dễ đọc",
        "prompt": "Bản tóm tắt có mạch lạc, các câu nối tiếp hợp lý, dễ đọc hiểu không? 5 = rất mạch lạc; 1 = rời rạc, khó hiểu.",
    },
}
PASS_THRESHOLD_PERCENT = 80.0
REVIEW_THRESHOLD_PERCENT = 65.0
FAITHFULNESS_HARD_FAIL_SCORE = 2  # faithfulness <= điểm này -> fail cứng nếu case zero-tolerance
VALID_RISKS = {"low", "medium", "high", "critical"}
ZERO_TOLERANCE_CATEGORIES = {"hallucination", "numeric_accuracy", "high_risk"}
CSV_FIELDS = [
    "id", "source_document", "category", "origin", "risk",
    "actual_summary", "word_count", "max_words", "length_pass",
    "numeric_flags", "criteria_breakdown", "overall_score_percent",
    "hallucinated_claims", "missing_key_points",
    "hard_fail", "auto_status", "manual_status", "final_status",
    "failure_reason", "latency_ms", "error", "reviewer", "review_notes",
]


class CriterionScore(BaseModel):
    name: Literal["faithfulness", "coverage", "conciseness", "coherence"]
    score: int = Field(ge=1, le=5)
    reasoning: str = Field(description="Giải thích ngắn gọn 1 câu vì sao chấm điểm này")


class SummaryJudgment(BaseModel):
    criteria: list[CriterionScore] = Field(
        description="Chấm đủ 4 tiêu chí: faithfulness, coverage, conciseness, coherence — mỗi tiêu chí đúng 1 lần"
    )
    hallucinated_claims: list[str] = Field(default_factory=list)
    missing_key_points: list[str] = Field(default_factory=list)


@dataclass
class JudgeResult:
    judgment: SummaryJudgment
    overall_score_percent: float
    metadata: dict[str, Any] = field(default_factory=dict)


DOCUMENT_CACHE: dict[str, str] = {}

DATE_PATTERN = re.compile(
    r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?"
    r"|ngày\s+\d{1,2}\s+tháng\s+\d{1,2}(?:\s+năm\s+\d{4})?",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?\s*%?")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate StudyFlow PDF Summary quality (LLM-as-judge, Gemini)")
    parser.add_argument("--dataset", default="eval/dataset_summary.jsonl")
    parser.add_argument("--output", default="eval/results_summary_run.csv")
    parser.add_argument("--summary-output", default="eval/summary_summary_run.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case-id")
    parser.add_argument("--manual-review", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with _path(str(path)).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"JSON không hợp lệ ở dòng {line_number}: {exc}") from exc
    return cases


def validate_dataset(cases: list[dict[str, Any]]) -> None:
    required = {"id", "source_document", "category", "risk", "origin"}
    ids: set[str] = set()
    for index, case in enumerate(cases, 1):
        missing = required - case.keys()
        if missing:
            raise ValueError(f"Case dòng {index} thiếu field: {', '.join(sorted(missing))}")
        if case["id"] in ids:
            raise ValueError(f"ID bị trùng: {case['id']}")
        ids.add(case["id"])
        if case["risk"] not in VALID_RISKS:
            raise ValueError(f"{case['id']}: risk không hợp lệ")
        if not isinstance(case["category"], list) or not case["category"]:
            raise ValueError(f"{case['id']}: category phải là list không rỗng")
        if not _path(case["source_document"]).is_file():
            raise ValueError(f"{case['id']}: không tìm thấy {case['source_document']}")


def filter_cases(cases: list[dict[str, Any]], limit: int | None, case_id: str | None) -> list[dict[str, Any]]:
    if case_id:
        selected = [case for case in cases if case["id"] == case_id]
        if not selected:
            raise ValueError(f"Không tìm thấy case-id {case_id}")
        return selected
    return cases[:limit] if limit is not None else cases


def get_document_text(path: str) -> str:
    resolved = str(_path(path).resolve())
    if resolved not in DOCUMENT_CACHE:
        file_path = Path(resolved)
        DOCUMENT_CACHE[resolved] = extract_pdf_text(
            file_path.read_bytes(), filename=file_path.name
        ).text
    return DOCUMENT_CACHE[resolved]


def extract_numeric_tokens(text: str) -> set[str]:
    """Trích mọi số / ngày tháng / % xuất hiện trong text, đã chuẩn hoá khoảng trắng."""
    tokens = set()
    for match in DATE_PATTERN.finditer(text):
        tokens.add(re.sub(r"\s+", " ", match.group().strip().lower()))
    for match in NUMBER_PATTERN.finditer(text):
        token = match.group().strip()
        if len(token.rstrip("%")) >= 1:  # bỏ qua match rỗng
            tokens.add(token.lower())
    return tokens


def check_numeric_consistency(source_text: str, summary_text: str) -> list[str]:
    """Trả về danh sách số/ngày xuất hiện trong tóm tắt nhưng KHÔNG có trong tài liệu gốc.
    Rule-based, không cần LLM và không cần đáp án mẫu — chỉ so tóm tắt với chính PDF gốc.
    Lưu ý: có thể có false positive nhẹ khi định dạng số bị viết lại (vd 1.000 vs 1000);
    coi đây là tín hiệu cần rà soát thêm, không phải tuyệt đối chính xác 100%.
    """
    summary_tokens = extract_numeric_tokens(summary_text)
    source_lower = source_text.lower()
    flags = [token for token in summary_tokens if token not in source_lower]
    return sorted(flags)


def _criteria_prompt_block() -> str:
    lines = []
    for name, spec in CRITERIA.items():
        lines.append(f"- {name} (trọng số {int(spec['weight']*100)}%): {spec['prompt']}")
    return "\n".join(lines)


def judge_summary(source_text: str, summary_text: str) -> JudgeResult:
    """Gọi Gemini làm giám khảo, chấm bản tóm tắt DỰA TRÊN CHÍNH TÀI LIỆU GỐC
    (reference-free — không cần bản tóm tắt mẫu). Judge chấm RIÊNG từng tiêu chí
    1-5 sao kèm lý do, rồi code tự tính % tổng theo trọng số cố định (không để
    model tự cộng điểm, tránh model tính sai)."""
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Thiếu GEMINI_API_KEY trong .env")
    model = os.getenv("GEMINI_JUDGE_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)
    instructions = (
        "Bạn là giám khảo chấm chất lượng bản tóm tắt tài liệu. Bạn sẽ nhận TOÀN VĂN "
        "tài liệu gốc và MỘT bản tóm tắt do AI khác tạo ra.\n\n"
        "Chấm đúng 4 tiêu chí sau, mỗi tiêu chí 1 điểm số nguyên từ 1 đến 5 kèm lý do ngắn gọn:\n"
        f"{_criteria_prompt_block()}\n\n"
        "Ngoài ra:\n"
        "- hallucinated_claims: liệt kê các câu/ý trong tóm tắt KHÔNG được tài liệu gốc hỗ trợ.\n"
        "- missing_key_points: liệt kê ý CHÍNH quan trọng trong tài liệu gốc bị tóm tắt bỏ sót.\n"
        "Chỉ đánh giá dựa trên nội dung tài liệu được cung cấp, không dùng kiến thức ngoài. "
        "Chấm nghiêm khắc, khách quan — không cho điểm cao mặc định."
    )
    response = client.models.generate_content(
        model=model,
        contents=f"TÀI LIỆU GỐC:\n{source_text}\n\nBẢN TÓM TẮT CẦN CHẤM:\n{summary_text}",
        config=genai_types.GenerateContentConfig(
            system_instruction=instructions,
            response_mime_type="application/json",
            response_schema=SummaryJudgment,
            temperature=0,
        ),
    )
    parsed = response.parsed
    if parsed is None:
        raise RuntimeError("Judge không trả response có cấu trúc")

    scores_by_name = {c.name: c.score for c in parsed.criteria}
    missing = set(CRITERIA) - set(scores_by_name)
    if missing:
        raise RuntimeError(f"Judge thiếu điểm cho tiêu chí: {sorted(missing)}")
    overall_score_percent = round(
        sum((scores_by_name[name] / 5) * spec["weight"] for name, spec in CRITERIA.items()) * 100, 1
    )
    return JudgeResult(judgment=parsed, overall_score_percent=overall_score_percent, metadata={"model": model})


def evaluate_case(case: dict[str, Any], source_text: str, summary_text: str, result: JudgeResult) -> dict[str, Any]:
    word_count = len(summary_text.split())
    max_words = case.get("max_words")
    length_pass = word_count <= max_words if max_words else True
    numeric_flags = check_numeric_consistency(source_text, summary_text)

    scores_by_name = {c.name: c.score for c in result.judgment.criteria}
    faithfulness_score = scores_by_name["faithfulness"]

    hard_fail_reasons: list[str] = []
    categories = set(case["category"])
    if categories & ZERO_TOLERANCE_CATEGORIES:
        if numeric_flags:
            hard_fail_reasons.append(f"Số liệu lạ không có trong tài liệu gốc: {numeric_flags}")
        if faithfulness_score <= FAITHFULNESS_HARD_FAIL_SCORE or result.judgment.hallucinated_claims:
            hard_fail_reasons.append(
                f"Faithfulness thấp ({faithfulness_score}/5) hoặc có hallucinated_claims: {result.judgment.hallucinated_claims}"
            )

    if hard_fail_reasons or not length_pass:
        auto_status = "FAIL"
    elif result.overall_score_percent < REVIEW_THRESHOLD_PERCENT:
        auto_status = "FAIL"
    elif result.overall_score_percent < PASS_THRESHOLD_PERCENT:
        auto_status = "REVIEW"
    else:
        auto_status = "PASS"

    reasons = []
    if numeric_flags:
        reasons.append("Số liệu không khớp tài liệu gốc")
    if result.judgment.hallucinated_claims:
        reasons.append(f"Có nội dung bịa: {result.judgment.hallucinated_claims}")
    if result.judgment.missing_key_points:
        reasons.append(f"Thiếu ý chính: {result.judgment.missing_key_points}")
    if not length_pass:
        reasons.append(f"Vượt giới hạn {max_words} từ (thực tế {word_count} từ)")

    return {
        "word_count": word_count, "length_pass": length_pass, "numeric_flags": numeric_flags,
        "hard_fail_reasons": hard_fail_reasons, "auto_status": auto_status,
        "failure_reason": "; ".join(reasons),
    }


def _base_row(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case["id"], "source_document": case["source_document"],
        "category": json.dumps(case["category"], ensure_ascii=False),
        "origin": case["origin"], "risk": case["risk"],
        "max_words": case.get("max_words", ""),
        "manual_status": "", "reviewer": "", "review_notes": "",
    }


def build_result_row(case: dict[str, Any], summary_text: str, result: JudgeResult,
                      evaluation: dict[str, Any], latency_ms: int, manual_review: bool) -> dict[str, Any]:
    row = _base_row(case)
    auto_status = "REVIEW" if manual_review else evaluation["auto_status"]
    criteria_breakdown = [
        {"name": c.name, "label": CRITERIA[c.name]["label"], "score": c.score, "reasoning": c.reasoning}
        for c in result.judgment.criteria
    ]
    row.update({
        "actual_summary": summary_text, "word_count": evaluation["word_count"],
        "length_pass": evaluation["length_pass"],
        "numeric_flags": json.dumps(evaluation["numeric_flags"], ensure_ascii=False),
        "criteria_breakdown": json.dumps(criteria_breakdown, ensure_ascii=False),
        "overall_score_percent": result.overall_score_percent,
        "hallucinated_claims": json.dumps(result.judgment.hallucinated_claims, ensure_ascii=False),
        "missing_key_points": json.dumps(result.judgment.missing_key_points, ensure_ascii=False),
        "hard_fail": json.dumps(evaluation["hard_fail_reasons"], ensure_ascii=False),
        "auto_status": auto_status, "final_status": auto_status,
        "failure_reason": evaluation["failure_reason"], "latency_ms": latency_ms, "error": "",
    })
    return row


def build_error_row(case: dict[str, Any], error: Exception, latency_ms: int) -> dict[str, Any]:
    row = _base_row(case)
    row.update({
        "actual_summary": "", "word_count": 0, "length_pass": False, "numeric_flags": "[]",
        "criteria_breakdown": "[]", "overall_score_percent": "",
        "hallucinated_claims": "[]", "missing_key_points": "[]", "hard_fail": "[]",
        "auto_status": "ERROR", "final_status": "ERROR",
        "failure_reason": "Pipeline error", "latency_ms": latency_ms, "error": repr(error),
    })
    return row


def write_results_csv(results: list[dict[str, Any]], output_path: str, overwrite: bool) -> None:
    path = _path(output_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} đã tồn tại; dùng --overwrite để ghi đè")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(results)


def build_summary(results: list[dict[str, Any]], dataset: str) -> dict[str, Any]:
    statuses = defaultdict(int)
    by_category: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"pass": 0, "total": 0})
    zero_violations = 0
    scored_percents = [row["overall_score_percent"] for row in results if row["overall_score_percent"] != ""]
    for row in results:
        status = row["final_status"]
        statuses[status] += 1
        categories = json.loads(row["category"])
        for category in categories:
            by_category[category]["total"] += 1
            if status == "PASS":
                by_category[category]["pass"] += 1
        if set(categories) & ZERO_TOLERANCE_CATEGORIES and status != "PASS":
            zero_violations += 1
    total = len(results)
    pass_rate = statuses["PASS"] / total if total else 0.0
    avg_score_percent = round(sum(scored_percents) / len(scored_percents), 1) if scored_percents else None
    return {
        "run_at": datetime.now().astimezone().isoformat(timespec="seconds"), "dataset": dataset,
        "total": total, "pass": statuses["PASS"], "fail": statuses["FAIL"],
        "error": statuses["ERROR"], "review": statuses["REVIEW"], "pass_rate": round(pass_rate, 4),
        "avg_score_percent": avg_score_percent,
        "pass_threshold_percent": PASS_THRESHOLD_PERCENT, "review_threshold_percent": REVIEW_THRESHOLD_PERCENT,
        "criteria_used": {
            name: {"weight_percent": int(spec["weight"] * 100), "label": spec["label"]}
            for name, spec in CRITERIA.items()
        },
        "zero_tolerance_rule": "Tóm tắt không được bịa số liệu/nội dung (faithfulness <= 2/5 hoặc có hallucinated_claims)",
        "zero_tolerance_violations": zero_violations, "zero_tolerance_passed": zero_violations == 0,
        "overall_passed": pass_rate >= 0.80 and zero_violations == 0,
        "by_category": dict(sorted(by_category.items())),
    }


def write_summary_json(summary: dict[str, Any], output_path: str, overwrite: bool) -> None:
    path = _path(output_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} đã tồn tại; dùng --overwrite để ghi đè")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def print_criteria_header() -> None:
    print("Tiêu chí đánh giá (LLM-as-judge, Gemini):")
    for name, spec in CRITERIA.items():
        print(f"  - {spec['label']} [{name}] — trọng số {int(spec['weight']*100)}%")
    print(f"Ngưỡng PASS: >= {PASS_THRESHOLD_PERCENT}%  |  Ngưỡng REVIEW: >= {REVIEW_THRESHOLD_PERCENT}%\n")


def print_case_result(result: dict[str, Any]) -> None:
    status = result["final_status"]
    percent = result["overall_score_percent"]
    percent_label = f"{percent}%" if percent != "" else "N/A"
    print(f"[{status}] {result['id']} — {percent_label} ({result['latency_ms']} ms)")
    if status == "ERROR":
        print(f"    error: {result['error']}")
        return
    for item in json.loads(result["criteria_breakdown"]):
        print(f"    - {item['label']}: {item['score']}/5 — {item['reasoning']}")
    if result["failure_reason"]:
        print(f"    lý do fail/review: {result['failure_reason']}")


def print_summary(summary: dict[str, Any]) -> None:
    print("\n" + "=" * 50 + "\nSUMMARY QUALITY EVALUATION REPORT\n" + "=" * 50)
    print(f"Total: {summary['total']}\nPASS: {summary['pass']}\nFAIL: {summary['fail']}\n"
          f"ERROR: {summary['error']}\nREVIEW: {summary['review']}")
    print(f"\nPass rate: {summary['pass_rate']:.2%}  |  Điểm % trung bình: {summary['avg_score_percent']}")
    print(f"Ngưỡng PASS: {summary['pass_threshold_percent']}%")
    print(f"\nZero-tolerance violations: {summary['zero_tolerance_violations']}")
    print(f"Overall result: {'PASSED' if summary['overall_passed'] else 'NOT PASSED'}\n" + "=" * 50)
    print("\nTiêu chí đã dùng để chấm:")
    for name, info in summary["criteria_used"].items():
        print(f"- {info['label']} [{name}]: {info['weight_percent']}%")
    print("\nBy category:")
    for category, value in summary["by_category"].items():
        print(f"- {category}: {value['pass']}/{value['total']}")


def main() -> int:
    args = parse_args()
    cases = load_jsonl(args.dataset)
    validate_dataset(cases)
    selected = filter_cases(cases, args.limit, args.case_id)
    print_criteria_header()
    results: list[dict[str, Any]] = []
    for case in selected:
        started = time.perf_counter()
        try:
            source_text = get_document_text(case["source_document"])
            summary_text = summarize_document(source_text)
            judge_result = judge_summary(source_text, summary_text)
            evaluation = evaluate_case(case, source_text, summary_text, judge_result)
            result = build_result_row(
                case, summary_text, judge_result, evaluation,
                round((time.perf_counter() - started) * 1000), args.manual_review,
            )
        except Exception as exc:
            result = build_error_row(case, exc, round((time.perf_counter() - started) * 1000))
        results.append(result)
        print_case_result(result)
    write_results_csv(results, args.output, args.overwrite)
    summary = build_summary(results, args.dataset)
    write_summary_json(summary, args.summary_output, args.overwrite)
    print_summary(summary)
    return 0 if summary["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())