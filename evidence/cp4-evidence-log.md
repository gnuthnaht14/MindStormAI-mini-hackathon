# CP4 Evidence Log — StudyFlow

Ngày tổng hợp: 2026-07-30  
Owner: Nhữ Trọng Thành  
Chuẩn sử dụng: B — working prototype + observed-use log + automated run.

## 1. Quan sát và phát biểu nguyên văn

Nguồn của năm dòng dưới đây là phiên làm việc trực tiếp giữa product owner và coding assistant ngày 2026-07-30. Đây là `n=1` với nhiều observation, không được diễn giải thành khảo sát thị trường.

| # | Phát biểu/ví dụ nguyên văn | Observation rút ra | Tác động vào spec |
|---|---|---|---|
| O-01 | “Bản tóm tắt này tôi đọc và cảm thấy còn nhiều chỗ khó hiểu.” | Summary hiện tại tạo được nhưng clarity chưa đạt nhu cầu học. | Chọn Summary phân tầng cho CP5; thêm clarity ≥4/5 vào quality bar. |
| O-02 | “trích xuất bằng pymu được nhưng gọi llm lại lỗi?” | Người dùng phân biệt được bước extract và generate nhưng UI lỗi 400 không giúp chẩn đoán. | Tách error theo lớp, không để một lỗi API bị hiểu là lỗi PDF. |
| O-03 | “sao tôi thấy app báo 400 nhưng trên log lại k phát hiện url nào 400” | Log đã bỏ mất phần thân lỗi upstream. | Lớp vận hành phải giữ status/request-id/error-code an toàn. |
| O-04 | “đâu đổi model ở đâu” | Cấu hình kỹ thuật trong UI làm luồng học khó hiểu. | Chuyển model/key về `.env`; UI chỉ giữ lựa chọn phục vụ học. |
| O-05 | “tôi không thấy nút đấy ở đâu” | Sidebar control bị CSS ẩn, làm mất đường correction/configuration. | Không ẩn control điều hướng bằng CSS; kiểm tra correction path. |

## 2. Bằng chứng working prototype

| Bằng chứng | Nơi kiểm tra | Kết quả |
|---|---|---|
| Upload/validate/extract PDF | `studyflow/src/studyflow/services/pdf_service.py` | PDF only, magic bytes, size, empty/image-only handling |
| One-call structured generation | `studyflow/src/studyflow/services/ai_service.py` | Responses API + Pydantic `StudyMaterial` |
| UI và state | `studyflow/app.py` | Upload → metrics → generate → tabs → download |
| Demo backup | `studyflow/sample/demo.pdf`, `demo_output.json` | Có input/output cố định khi API hoặc mạng lỗi |
| Unit test | `python -m unittest discover -s studyflow/tests -p "test_*.py" -v` | 10/10 PASS ngày 2026-07-30 |
| Runtime health | `GET http://localhost:8501/_stcore/health` | HTTP 200, body `ok` ngày 2026-07-30 |

## 3. Eval log — không chỉnh expected sau khi chạy

Nguồn: `studyflow/eval/results_first_run.csv` và `studyflow/eval/summary_first_run.json`.

```text
run_at: 2026-07-30T16:01:18+07:00
dataset: eval/dataset.jsonl
total: 20
pass: 18
fail: 2
error: 0
review: 0
pass_rate: 90.00%
threshold: 80.00%
zero_tolerance_violations: 0
overall_automated_result: PASSED
```

Fail được giữ lại:

- `EVAL-014`: expected/actual action đều `CLARIFY`; fail do thiếu đúng cụm `must_include`.
- `EVAL-016`: expected/actual action đều `CLARIFY`; fail do thiếu đúng cụm `must_include`.

Giới hạn: bộ này đo decision policy/Q&A tốt hơn clarity của summary. CP5 phải bổ sung human validation, không được lấy pass rate 90% để tuyên bố summary đã dễ hiểu.

## 4. Commit trail

```text
50cc629 update checkpoint 2
894b286 demo chạy AI lần đầu, chưa bao gồm eval
98fb3c1 update tóm tắt tài liệu chạy open_ai_key
2e06ddf update eval
ca070d8 update tạo câu hỏi
a475f51 update ui/ux hidden sidebar and lll_api
```

## 5. Evidence còn thiếu trước CP5

- Hai willing users có tên ngoài product owner.
- Ba lượt test summary với cùng bộ ba câu hỏi trong `spec.md` §8.
- Latency thực tế của happy path trên máy/mạng demo.
- Đối chiếu citation theo trang cho Summary V2.
