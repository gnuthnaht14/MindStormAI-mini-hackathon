"""Xuất biểu đồ trực quan từ kết quả eval_summary.py.

Cách chạy (đứng ở thư mục gốc project, cùng cấp app.py):
    pip install matplotlib
    python eval/plot_results.py

Mặc định đọc eval/results_summary_run.csv + eval/summary_summary_run.json,
xuất ra eval/eval_report.png (đổi bằng --results/--summary/--output).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]

STATUS_COLORS = {"PASS": "#2ecc71", "REVIEW": "#f1c40f", "FAIL": "#e74c3c", "ERROR": "#7f8c8d"}
CRITERIA_LABELS = {
    "faithfulness": "Trung thực",
    "coverage": "Bao quát",
    "conciseness": "Súc tích",
    "coherence": "Mạch lạc",
}


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vẽ biểu đồ kết quả eval_summary.py")
    parser.add_argument("--results", default="eval/results_summary_run.csv")
    parser.add_argument("--summary", default="eval/summary_summary_run.json")
    parser.add_argument("--output", default="eval/eval_report.png")
    return parser.parse_args()


def load_results(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_summary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def plot(results: list[dict], summary: dict, output_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Báo cáo chất lượng tóm tắt (eval_summary.py)", fontsize=15, fontweight="bold")

    # 1) Điểm % từng case, tô màu theo trạng thái, kèm ngưỡng pass/review
    ax = axes[0, 0]
    scored = [r for r in results if r["overall_score_percent"] not in ("", None)]
    if scored:
        ids = [r["id"] for r in scored]
        scores = [float(r["overall_score_percent"]) for r in scored]
        colors = [STATUS_COLORS.get(r["final_status"], "#7f8c8d") for r in scored]
        ax.bar(ids, scores, color=colors)
        ax.axhline(summary["pass_threshold_percent"], color="#2ecc71", linestyle="--", linewidth=1, label="Ngưỡng PASS")
        ax.axhline(summary["review_threshold_percent"], color="#f1c40f", linestyle="--", linewidth=1, label="Ngưỡng REVIEW")
        ax.set_ylim(0, 100)
        ax.set_ylabel("overall_score_percent (%)")
        ax.set_title("Điểm % từng case")
        ax.tick_params(axis="x", rotation=45)
        ax.legend(fontsize=8)
    else:
        ax.text(0.5, 0.5, "Không có case nào có điểm", ha="center", va="center")
        ax.set_axis_off()

    # 2) Phân bố PASS / REVIEW / FAIL / ERROR
    ax = axes[0, 1]
    status_order = ["PASS", "REVIEW", "FAIL", "ERROR"]
    counts = [summary.get(key.lower(), 0) for key in status_order]
    bars = ax.bar(status_order, counts, color=[STATUS_COLORS[s] for s in status_order])
    ax.set_title(f"Phân bố kết quả (tổng {summary['total']} case)")
    ax.set_ylabel("Số case")
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(count), ha="center", va="bottom")

    # 3) Điểm trung bình theo từng tiêu chí (faithfulness/coverage/conciseness/coherence)
    ax = axes[1, 0]
    criterion_totals: dict[str, list[int]] = {name: [] for name in CRITERIA_LABELS}
    for row in results:
        breakdown = row.get("criteria_breakdown") or "[]"
        try:
            items = json.loads(breakdown)
        except json.JSONDecodeError:
            continue
        for item in items:
            if item["name"] in criterion_totals:
                criterion_totals[item["name"]].append(item["score"])
    names = list(CRITERIA_LABELS)
    averages = [sum(v) / len(v) if v else 0 for v in (criterion_totals[n] for n in names)]
    labels = [CRITERIA_LABELS[n] for n in names]
    ax.barh(labels, averages, color="#5b6ee1")
    ax.set_xlim(0, 5)
    ax.set_xlabel("Điểm trung bình (/5)")
    ax.set_title("Điểm trung bình theo từng tiêu chí")
    for i, value in enumerate(averages):
        ax.text(value, i, f" {value:.2f}", va="center")

    # 4) Pass rate theo category
    ax = axes[1, 1]
    by_category = summary.get("by_category", {})
    categories = list(by_category)
    rates = [
        (by_category[c]["pass"] / by_category[c]["total"] * 100) if by_category[c]["total"] else 0
        for c in categories
    ]
    ax.bar(categories, rates, color="#9b6ede")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Pass rate (%)")
    ax.set_title("Pass rate theo category")
    ax.tick_params(axis="x", rotation=30)
    for i, (cat, rate) in enumerate(zip(categories, rates)):
        total = by_category[cat]["total"]
        passed = by_category[cat]["pass"]
        ax.text(i, rate, f"{passed}/{total}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    print(f"Đã lưu biểu đồ tại: {output_path}")


def main() -> None:
    args = parse_args()
    results = load_results(_path(args.results))
    summary = load_summary(_path(args.summary))
    plot(results, summary, _path(args.output))


if __name__ == "__main__":
    main()