import csv, json, sys

path = sys.argv[1] if len(sys.argv) > 1 else "eval/results_summary_run.csv"
case_id = sys.argv[2] if len(sys.argv) > 2 else None

with open(path, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        if case_id and row["id"] != case_id:
            continue
        print("=" * 60)
        print(f"ID: {row['id']}  |  final_status: {row['final_status']}  |  overall_score_percent: {row['overall_score_percent']}%")
        print(f"hard_fail: {row['hard_fail']}")
        print(f"failure_reason: {row['failure_reason']}")
        print("-" * 60)
        print("CHẤM ĐIỂM THEO TIÊU CHÍ:")
        for item in json.loads(row["criteria_breakdown"]):
            print(f"  - {item['label']} [{item['name']}]: {item['score']}/5")
            print(f"    -> {item['reasoning']}")
        print("-" * 60)
        hallucinated = json.loads(row["hallucinated_claims"])
        missing = json.loads(row["missing_key_points"])
        if hallucinated:
            print(f"HALLUCINATED CLAIMS: {hallucinated}")
        if missing:
            print(f"MISSING KEY POINTS: {missing}")
        print("-" * 60)
        print("SUMMARY THỰC TẾ:")
        print(row["actual_summary"])
        print()