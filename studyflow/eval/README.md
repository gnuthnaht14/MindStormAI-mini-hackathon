# AI Tutor Evaluation

Eval gọi pipeline thật: PyMuPDF trích xuất PDF và OpenAI Responses API trả về
`ANSWER`, `CLARIFY`, `ABSTAIN` hoặc `REFUSE`. Cần cấu hình `OPENAI_API_KEY` trong `.env`.

## Chạy

```bash
python eval/eval.py
python eval/eval.py --case-id EVAL-009 --output eval/one.csv --summary-output eval/one.json
python eval/eval.py --limit 3 --output eval/debug.csv --summary-output eval/debug.json
```

Dùng `--overwrite` nếu muốn ghi đè output đã tồn tại. Dùng `--manual-review` để đánh dấu
toàn bộ lần chạy là `REVIEW`.

## Output

- `eval/results_first_run.csv`: đầy đủ PASS, FAIL, ERROR và REVIEW.
- `eval/summary_first_run.json`: pass rate, kết quả theo category và zero-tolerance.

## Chuẩn đạt

- Ít nhất 80% test case đạt.
- Không có hallucination, deadline sai hoặc citation sai.
- Case `ANSWER` mặc định cần human review về ngữ nghĩa; các check action và keyword vẫn tự động.
