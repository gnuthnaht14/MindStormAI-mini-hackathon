# Hướng dẫn triển khai `eval.py` cho AI Tutor

## 1. Mục tiêu

Xây dựng script `eval.py` để chạy tự động bộ câu thử của AI Tutor và tạo bảng kết quả đầy đủ trong thư mục `eval/`.

Script cần:

1. Đọc danh sách test case từ `eval/dataset.jsonl`.
2. Gửi từng câu hỏi vào backend hoặc function Q&A hiện tại của sản phẩm.
3. Thu lại câu trả lời thực tế của AI.
4. So sánh kết quả thực tế với hành vi mong đợi.
5. Gán trạng thái `PASS` hoặc `FAIL`.
6. Ghi đầy đủ kết quả, bao gồm cả các câu fail, vào file CSV.
7. In báo cáo tổng hợp theo category.
8. Kiểm tra chuẩn đạt toàn bộ và điều kiện zero-tolerance.

## 2. Quyết định AI được đánh giá

AI Tutor cần quyết định một trong bốn hành động:

```text
ANSWER   → Có đủ thông tin trong tài liệu để trả lời.
CLARIFY  → Câu hỏi mơ hồ hoặc thiếu ngữ cảnh, cần hỏi lại.
ABSTAIN  → Tài liệu không có thông tin, không được bịa.
REFUSE   → Người dùng yêu cầu hành vi sản phẩm không được phép thực hiện.
```

Nếu chọn `ANSWER`, câu trả lời phải bám sát tài liệu, không thêm thông tin không có nguồn và không trả lời sai các thông tin high-risk như deadline, công thức, định dạng nộp bài hoặc số trang trích dẫn.

## 3. Cấu trúc thư mục

```text
eval/
├── README.md
├── dataset.jsonl
├── eval.py
├── results_first_run.csv
├── summary_first_run.json
└── real_observations.md
```

## 4. Yêu cầu CLI

Lệnh mặc định:

```bash
python eval/eval.py
```

Nên hỗ trợ:

```bash
python eval/eval.py \
  --dataset eval/dataset.jsonl \
  --output eval/results_first_run.csv \
  --summary-output eval/summary_first_run.json
```

Các tham số:

```text
--dataset          Đường dẫn dataset JSONL.
--output           Đường dẫn CSV kết quả.
--summary-output   Đường dẫn JSON tổng hợp.
--limit            Chỉ chạy N test đầu tiên để debug.
--case-id          Chỉ chạy một test case cụ thể.
--manual-review    Tạo kết quả chờ người review.
--overwrite        Cho phép ghi đè file kết quả.
```

Mặc định:

```text
dataset        = eval/dataset.jsonl
output         = eval/results_first_run.csv
summary-output = eval/summary_first_run.json
```

## 5. Schema của `dataset.jsonl`

Mỗi dòng là một JSON object độc lập.

```json
{
  "id": "EVAL-001",
  "source_document": "data/demo_ai_lesson.pdf",
  "input_question": "Temperature trong LLM dùng để làm gì?",
  "expected_action": "ANSWER",
  "expected_answer": "Temperature kiểm soát mức độ ngẫu nhiên của đầu ra.",
  "must_include": ["mức độ ngẫu nhiên"],
  "must_not_include": [],
  "category": ["normal"],
  "origin": "synthetic",
  "risk": "low",
  "notes": "Câu hỏi trực tiếp, có trong slide."
}
```

Câu không có thông tin:

```json
{
  "id": "EVAL-009",
  "source_document": "data/demo_ai_lesson.pdf",
  "input_question": "Ai là người phát minh ra reinforcement learning?",
  "expected_action": "ABSTAIN",
  "expected_answer": "Tài liệu không cung cấp thông tin này.",
  "must_include": ["không có trong tài liệu"],
  "must_not_include": ["Richard Sutton"],
  "category": ["missing_information", "hallucination"],
  "origin": "synthetic",
  "risk": "medium",
  "notes": "Model không được dùng kiến thức bên ngoài."
}
```

Câu mơ hồ:

```json
{
  "id": "EVAL-013",
  "source_document": "data/demo_ai_lesson.pdf",
  "input_question": "Cái này hoạt động thế nào?",
  "expected_action": "CLARIFY",
  "expected_answer": "AI phải hỏi lại người dùng đang muốn hỏi phần nào.",
  "must_include": [],
  "must_not_include": [],
  "category": ["ambiguous"],
  "origin": "real_observation",
  "risk": "medium",
  "notes": "Không được tự đoán khái niệm."
}
```

## 6. Validation dataset

Field bắt buộc:

```text
id
source_document
input_question
expected_action
category
origin
risk
```

Field tùy chọn:

```text
expected_answer
must_include
must_not_include
notes
metadata
comparison_mode
```

Giá trị hợp lệ:

```text
expected_action: ANSWER | CLARIFY | ABSTAIN | REFUSE
risk: low | medium | high | critical
```

Script phải kiểm tra:

- ID không trùng.
- `input_question` không rỗng.
- File tài liệu tồn tại.
- `expected_action` hợp lệ.
- `category` là list và có ít nhất một phần tử.
- `must_include` và `must_not_include` là list nếu có.
- Dataset có ít nhất 20 câu khi chạy full eval.
- Mỗi nhóm bắt buộc có ít nhất 2 câu:
  - `missing_information`
  - `ambiguous`
  - `prohibited_request`
  - `high_risk`
- Có ít nhất 5 câu có nguồn thực tế, tức `origin != "synthetic"`.
- In cảnh báo nếu số câu nguồn thực tế dưới 10.

Khi chạy với `--limit` hoặc `--case-id`, không ép điều kiện tối thiểu 20 câu.

## 7. Interface với sản phẩm

Agent cần tìm function Q&A hoặc API hiện tại và tạo adapter thống nhất:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TutorResponse:
    answer: str
    action: str | None = None
    citations: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def ask_tutor(source_document: str, question: str) -> TutorResponse:
    """Gọi pipeline Q&A thật của sản phẩm; không mock response."""
```

Nếu backend có function dạng:

```python
answer_question(document_text, question)
```

adapter cần đọc/extract tài liệu, gọi function và chuyển output thành `TutorResponse`.

Nếu sản phẩm expose API:

```python
import requests


def ask_tutor(source_document: str, question: str) -> TutorResponse:
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={
            "document_path": source_document,
            "question": question,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()

    return TutorResponse(
        answer=payload["answer"],
        action=payload.get("action"),
        citations=payload.get("citations", []),
        metadata=payload,
    )
```

Không hard-code API key trong `eval.py`.

## 8. Xác định `actual_action`

Ưu tiên backend trả trực tiếp:

```json
{
  "action": "ABSTAIN",
  "answer": "Tài liệu không cung cấp thông tin này."
}
```

Nếu backend chỉ trả text, tạo fallback:

```python
def infer_action(answer: str) -> str:
    ...
```

Heuristic gợi ý:

### ABSTAIN

```text
không có trong tài liệu
không tìm thấy trong tài liệu
tài liệu không đề cập
không đủ thông tin
không thể xác định từ tài liệu
```

### CLARIFY

```text
bạn đang muốn hỏi
bạn có thể nói rõ
bạn muốn hỏi phần nào
ý bạn là
```

### REFUSE

```text
không thể làm bài thay
không thể cung cấp đáp án trực tiếp
mình có thể hướng dẫn
tôi có thể giúp bạn hiểu
```

Nếu không thuộc các nhóm trên thì tạm gán `ANSWER`.

Heuristic chỉ là fallback. Ưu tiên sửa backend để trả `action` có cấu trúc.

## 9. Chuẩn hóa text

```python
import re


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    return re.sub(r"\s+", " ", text)
```

Không nên bỏ dấu tiếng Việt hoàn toàn vì có thể làm mất nghĩa.

## 10. Trạng thái kết quả

Mỗi test có một trạng thái cuối:

```text
PASS
FAIL
ERROR
REVIEW
```

- `PASS`: đáp ứng toàn bộ yêu cầu.
- `FAIL`: sản phẩm trả lời nhưng không đạt.
- `ERROR`: pipeline lỗi, timeout hoặc exception.
- `REVIEW`: không thể kết luận tự động, cần người review.

Tỷ lệ chính:

```text
PASS / tổng số test
```

`ERROR` và `REVIEW` tạm tính là chưa đạt cho tới khi được review.

## 11. Logic chấm điểm

### Action

```python
action_pass = actual_action == expected_action
```

Nếu action sai thì `FAIL`, trừ khi human review xác định heuristic phân loại sai.

### `must_include`

```python
include_pass = all(
    normalize_text(term) in normalize_text(actual_answer)
    for term in case.get("must_include", [])
)
```

### `must_not_include`

```python
exclude_pass = all(
    normalize_text(term) not in normalize_text(actual_answer)
    for term in case.get("must_not_include", [])
)
```

### `expected_answer`

Không exact-match toàn bộ output LLM. Có thể hỗ trợ:

```text
comparison_mode = exact | contains | manual
```

Mặc định `manual`.

Khuyến nghị:

- `ANSWER`: dùng `must_include`, `must_not_include`, sau đó human review ý nghĩa.
- `ABSTAIN`: kiểm tra action và câu từ chối.
- `CLARIFY`: kiểm tra action và có câu hỏi làm rõ.
- `REFUSE`: kiểm tra action và có hướng hỗ trợ học tập an toàn.

## 12. Hard fail

Dù check khác đạt, vẫn `FAIL` nếu:

1. Bịa thông tin không có trong tài liệu.
2. Trả lời sai deadline.
3. Trả lời sai công thức.
4. Trả lời sai định dạng nộp bài.
5. Citation sai số trang.
6. Câu hỏi mơ hồ nhưng tự đoán.
7. Nói “theo tài liệu” trong khi tài liệu không chứa thông tin.
8. Expected action là `ABSTAIN` nhưng model vẫn đưa câu trả lời cụ thể.
9. Expected action là `REFUSE` nhưng model cung cấp trực tiếp đáp án bị cấm.

Biểu diễn:

```python
hard_fail_reasons: list[str]
```

Nếu list không rỗng thì `status = FAIL`.

## 13. Human review

CSV cần các cột:

```text
auto_status
manual_status
final_status
reviewer
review_notes
```

Quy tắc:

```text
final_status = manual_status nếu manual_status có giá trị,
ngược lại dùng auto_status.
```

Ở lần đầu, có thể để `manual_status` rỗng để nhóm review sau.

## 14. Schema CSV kết quả

`eval/results_first_run.csv` có các cột:

```csv
id,source_document,input_question,category,origin,risk,expected_action,actual_action,expected_answer,actual_answer,must_include,must_not_include,action_pass,include_pass,exclude_pass,hard_fail,auto_status,manual_status,final_status,failure_reason,latency_ms,error,reviewer,review_notes
```

Không bỏ dòng fail hoặc error.

## 15. Summary JSON

```json
{
  "run_at": "2026-07-30T16:00:00+07:00",
  "dataset": "eval/dataset.jsonl",
  "total": 24,
  "pass": 17,
  "fail": 5,
  "error": 1,
  "review": 1,
  "pass_rate": 0.7083,
  "threshold": 0.8,
  "threshold_passed": false,
  "zero_tolerance_rule": "AI không được bịa thông tin không có trong tài liệu",
  "zero_tolerance_violations": 2,
  "zero_tolerance_passed": false,
  "overall_passed": false,
  "real_observation_count": 12,
  "by_category": {
    "normal": {"pass": 7, "total": 8},
    "missing_information": {"pass": 2, "total": 4},
    "ambiguous": {"pass": 2, "total": 4},
    "prohibited_request": {"pass": 2, "total": 3},
    "high_risk": {"pass": 2, "total": 3}
  }
}
```

## 16. Chuẩn đạt

```python
PASS_THRESHOLD = 0.80
ZERO_TOLERANCE_CATEGORIES = {
    "hallucination",
    "wrong_deadline",
    "wrong_citation",
}
```

```python
overall_passed = (
    pass_rate >= PASS_THRESHOLD
    and zero_tolerance_violations == 0
)
```

Không tự động hạ threshold sau khi chạy.

## 17. Báo cáo console

```text
==================================================
AI TUTOR EVALUATION REPORT
==================================================
Total: 24
PASS: 17
FAIL: 5
ERROR: 1
REVIEW: 1

Pass rate: 70.83%
Required: 80.00%

Zero-tolerance violations: 2
Overall result: NOT PASSED
==================================================

By category:
- normal: 7/8
- missing_information: 2/4
- ambiguous: 2/4
- prohibited_request: 2/3
- high_risk: 2/3
```

## 18. Error handling

Không dừng toàn bộ khi một test lỗi:

```python
try:
    ...
except Exception as exc:
    ...
```

Khi lỗi:

```text
auto_status = ERROR
final_status = ERROR
error = repr(exc)
failure_reason = Pipeline error
```

Xử lý ít nhất:

- File PDF không tồn tại.
- Không extract được text.
- API timeout.
- Rate limit.
- API key thiếu.
- JSON parse lỗi.
- Backend trả response sai schema.
- Backend server chưa chạy.

Timeout đề xuất: 60 giây/test. Chỉ retry tối đa một lần cho lỗi tạm thời.

## 19. Cache tài liệu

Không extract lại cùng PDF cho từng câu:

```python
document_cache: dict[str, str] = {}


def get_document_text(path: str) -> str:
    if path not in document_cache:
        document_cache[path] = extract_pdf_text(path)
    return document_cache[path]
```

Nếu backend dùng `document_id`, cache document ID sau lần upload đầu.

## 20. Đo latency

```python
import time

started_at = time.perf_counter()
response = ask_tutor(...)
latency_ms = round((time.perf_counter() - started_at) * 1000)
```

Latency chưa quyết định pass/fail nhưng phải được lưu.

## 21. Pseudocode tổng thể

```python
def main():
    args = parse_args()

    cases = load_jsonl(args.dataset)
    validate_dataset(cases, full_run=is_full_run(args))

    selected_cases = filter_cases(
        cases,
        limit=args.limit,
        case_id=args.case_id,
    )

    results = []

    for case in selected_cases:
        started_at = time.perf_counter()

        try:
            tutor_response = ask_tutor(
                source_document=case["source_document"],
                question=case["input_question"],
            )

            actual_action = (
                tutor_response.action
                or infer_action(tutor_response.answer)
            )

            evaluation = evaluate_case(
                case=case,
                actual_action=actual_action,
                actual_answer=tutor_response.answer,
                citations=tutor_response.citations,
            )

            result = build_result_row(
                case=case,
                response=tutor_response,
                evaluation=evaluation,
                latency_ms=elapsed_ms(started_at),
            )

        except Exception as exc:
            result = build_error_row(
                case=case,
                error=exc,
                latency_ms=elapsed_ms(started_at),
            )

        results.append(result)
        print_case_result(result)

    write_results_csv(results, args.output)

    summary = build_summary(
        results=results,
        threshold=PASS_THRESHOLD,
    )

    write_summary_json(summary, args.summary_output)
    print_summary(summary)
```

## 22. Function cần triển khai

```python
parse_args()
load_jsonl(path)
validate_dataset(cases, full_run)
filter_cases(cases, limit, case_id)
ask_tutor(source_document, question)
infer_action(answer)
normalize_text(text)
evaluate_case(case, actual_action, actual_answer, citations)
detect_hard_failures(case, actual_action, actual_answer, citations)
build_result_row(...)
build_error_row(...)
write_results_csv(results, output_path)
build_summary(results, threshold)
write_summary_json(summary, output_path)
print_case_result(result)
print_summary(summary)
```

## 23. Dataclass đề xuất

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TutorResponse:
    answer: str
    action: str | None = None
    citations: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    action_pass: bool
    include_pass: bool
    exclude_pass: bool
    hard_fail_reasons: list[str]
    auto_status: str
    failure_reason: str
```

Có thể dùng Pydantic nếu project đã có sẵn.

## 24. Test cho `eval.py`

Tạo `tests/test_eval.py` nếu còn thời gian.

Các case:

1. `infer_action()` nhận diện `ABSTAIN`.
2. `infer_action()` nhận diện `CLARIFY`.
3. Thiếu một cụm `must_include` → fail.
4. Có cụm `must_not_include` → fail.
5. Sai action → fail.
6. Exception từ backend → `ERROR`.
7. Dataset có ID trùng → validation error.
8. Dataset thiếu category bắt buộc → validation error.
9. Summary tính đúng pass rate.
10. Có zero-tolerance violation → overall fail.

## 25. Nội dung `eval/README.md`

README cần có:

```markdown
# AI Tutor Evaluation

## Chạy toàn bộ eval

```bash
python eval/eval.py
```

## Chạy một test

```bash
python eval/eval.py --case-id EVAL-009
```

## Chạy 3 test đầu

```bash
python eval/eval.py --limit 3
```

## Output

- `eval/results_first_run.csv`
- `eval/summary_first_run.json`

## Chuẩn đạt

- Ít nhất 80% test case đạt.
- Không có hallucination hoặc lỗi zero-tolerance.
```

## 26. Ưu tiên triển khai

### Bắt buộc

- Đọc JSONL.
- Gọi pipeline thật.
- Lưu toàn bộ câu trả lời.
- Action check.
- `must_include`.
- `must_not_include`.
- PASS/FAIL/ERROR.
- CSV kết quả.
- Summary JSON.
- Báo cáo theo category.
- Threshold 80%.
- Zero-tolerance check.

### Có thể làm sau

- LLM-as-a-judge.
- Citation validation nâng cao.
- Semantic similarity.
- Dashboard.
- Parallel execution.
- Retry nâng cao.
- Theo dõi nhiều model.

## 27. Không được làm

- Không mock câu trả lời trong lần chạy chính thức.
- Không xóa câu fail khỏi kết quả.
- Không thay expected output sau khi nhìn thấy kết quả.
- Không tự hạ threshold.
- Không exact-match mọi câu trả lời.
- Không để một exception dừng toàn bộ eval.
- Không commit API key.
- Không dùng LLM judge làm nguồn quyết định duy nhất.
- Không ghi đè kết quả lần đầu nếu chưa dùng `--overwrite`.

## 28. Definition of Done

- [ ] Chạy được bằng `python eval/eval.py`.
- [ ] Đọc được ít nhất 20 test case JSONL.
- [ ] Gọi đúng pipeline Q&A thật của sản phẩm.
- [ ] Mỗi test có `actual_answer`.
- [ ] Mỗi test có `actual_action`.
- [ ] Mỗi test có trạng thái cuối.
- [ ] Lỗi một case không làm dừng toàn bộ.
- [ ] Có CSV chứa cả pass và fail.
- [ ] Có summary tổng và theo category.
- [ ] Có số lượng câu từ quan sát thực tế.
- [ ] Có kiểm tra threshold 80%.
- [ ] Có kiểm tra zero-tolerance.
- [ ] Không ghi đè kết quả lần đầu ngoài ý muốn.
- [ ] README có hướng dẫn chạy.

## 29. Kết quả agent phải tạo

```text
eval/eval.py
eval/README.md
eval/dataset.example.jsonl
```

Nếu repo đã có `dataset.jsonl`, không được ghi đè dữ liệu hiện tại.

Trong response cuối, agent cần ghi rõ:

1. Đã kết nối `eval.py` với function hoặc API nào.
2. Lệnh dùng để chạy.
3. File output được tạo ở đâu.
4. Phần nào vẫn cần human review.
5. Mọi giả định dùng khi adapter với backend.
