# CP4 Evidence Log — StudyFlow

Ngày tổng hợp: 2026-07-30  
Owner: Nhữ Trọng Thành  
Chuẩn sử dụng: A — khảo sát `n=51`; B — working prototype + observed-use log + automated run.

## 1. Khảo sát nhu cầu — 51 người trả lời

Nguồn: bốn biểu đồ tổng hợp Google Forms do product owner cung cấp ngày 2026-07-30. Đây là dữ liệu aggregate; report không kèm danh tính hoặc câu trả lời theo từng respondent. Với câu checkbox, tỷ lệ có thể cộng vượt 100% và không được cộng để suy ra số người duy nhất.

### 1.1. Khó khăn khi ôn tập sau buổi học

| Lựa chọn trong report | Số người | Tỷ lệ |
|---|---:|---:|
| Quá nhiều thông tin, khó xác định phần trọng tâm | 30/51 | 58,8% |
| Mất nhiều thời gian để đọc lại slide | 29/51 | 56,9% |
| Không có câu hỏi để tự kiểm tra | 23/51 | 45,1% |
| Có bản tóm tắt nhưng vẫn gặp trở ngại (nhãn trong ảnh nguồn bị rút gọn) | 20/51 | 39,2% |
| Thường không ôn lại sau buổi học | 13/51 | 25,5% |
| Không gặp khó khăn | 9/51 | 17,6% |
| Khác | 1/51 | 2,0% |

Kết luận được phép rút ra: hai pain phổ biến nhất là quá tải thông tin và thời gian đọc lại. Không suy ra `42/51 có khó khăn` bằng cách lấy `51 - 9`, vì câu hỏi checkbox không chứng minh lựa chọn “không khó khăn” là exclusive.

### 1.2. Chức năng mong muốn từ AI Tutor

| Chức năng | Số người | Tỷ lệ |
|---|---:|---:|
| Liệt kê kiến thức trọng tâm | 34/51 | 66,7% |
| Tự động tổng hợp và tóm tắt nội dung | 27/51 | 52,9% |
| Tạo câu hỏi trắc nghiệm để ôn tập | 26/51 | 51,0% |
| Cho phép hỏi lại nội dung bài học | 21/51 | 41,2% |
| Giải thích đáp án và phần kiến thức liên quan | 20/51 | 39,2% |
| Tạo câu hỏi tự luận để kiểm tra | 14/51 | 27,5% |
| Khác | 0/51 | 0% |

### 1.3. Một chức năng quan trọng nhất

| Chức năng | Số người suy ra từ 51 responses | Tỷ lệ report |
|---|---:|---:|
| Xác định kiến thức trọng tâm | 22 | 43,1% |
| Tóm tắt bài học | 12 | 23,5% |
| Hỏi đáp về nội dung bài học | 7 | 13,7% |
| Tạo câu hỏi ôn tập | 6 | 11,8% |
| Giải thích đáp án | 4 | 7,8% |

Hai nhu cầu thuộc lõi summary — xác định trọng tâm và tóm tắt — chiếm `34/51 = 66,7%` lựa chọn quan trọng nhất. Đây là căn cứ định lượng chính để chọn lát cắt Summary + Key concepts.

### 1.4. Mức quan tâm tới summary + bộ câu hỏi tự động

| Điểm | Số người | Tỷ lệ |
|---:|---:|---:|
| 1 | 2 | 3,9% |
| 2 | 2 | 3,9% |
| 3 | 16 | 31,4% |
| 4 | 17 | 33,3% |
| 5 | 14 | 27,5% |

- Điểm trung bình: `(1×2 + 2×2 + 3×16 + 4×17 + 5×14) / 51 = 3,76/5`.
- Chấm 4–5: `31/51 = 60,8%`.
- Chấm từ 3 trở lên: `47/51 = 92,2%`.
- Chấm 1–2: `4/51 = 7,8%`.

## 2. Quan sát và phát biểu nguyên văn

Nguồn của năm dòng dưới đây là phiên làm việc trực tiếp giữa product owner và coding assistant ngày 2026-07-30. Đây là `n=1` với nhiều observation, không được diễn giải thành khảo sát thị trường.

| # | Phát biểu/ví dụ nguyên văn | Observation rút ra | Tác động vào spec |
|---|---|---|---|
| O-01 | “Bản tóm tắt này tôi đọc và cảm thấy còn nhiều chỗ khó hiểu.” | Summary hiện tại tạo được nhưng clarity chưa đạt nhu cầu học. | Chọn Summary phân tầng cho CP5; thêm clarity ≥4/5 vào quality bar. |
| O-02 | “trích xuất bằng pymu được nhưng gọi llm lại lỗi?” | Người dùng phân biệt được bước extract và generate nhưng UI lỗi 400 không giúp chẩn đoán. | Tách error theo lớp, không để một lỗi API bị hiểu là lỗi PDF. |
| O-03 | “sao tôi thấy app báo 400 nhưng trên log lại k phát hiện url nào 400” | Log đã bỏ mất phần thân lỗi upstream. | Lớp vận hành phải giữ status/request-id/error-code an toàn. |
| O-04 | “đâu đổi model ở đâu” | Cấu hình kỹ thuật trong UI làm luồng học khó hiểu. | Chuyển model/key về `.env`; UI chỉ giữ lựa chọn phục vụ học. |
| O-05 | “tôi không thấy nút đấy ở đâu” | Sidebar control bị CSS ẩn, làm mất đường correction/configuration. | Không ẩn control điều hướng bằng CSS; kiểm tra correction path. |

## 3. Bằng chứng working prototype

| Bằng chứng | Nơi kiểm tra | Kết quả |
|---|---|---|
| Upload/validate/extract PDF | `studyflow/src/studyflow/services/pdf_service.py` | PDF only, magic bytes, size, empty/image-only handling |
| One-call structured generation | `studyflow/src/studyflow/services/ai_service.py` | Responses API + Pydantic `StudyMaterial` |
| UI và state | `studyflow/app.py` | Upload → metrics → generate → tabs → download |
| Demo backup | `studyflow/sample/demo.pdf`, `demo_output.json` | Có input/output cố định khi API hoặc mạng lỗi |
| Unit test | `python -m unittest discover -s studyflow/tests -p "test_*.py" -v` | 10/10 PASS ngày 2026-07-30 |
| Runtime health | `GET http://localhost:8501/_stcore/health` | HTTP 200, body `ok` ngày 2026-07-30 |

## 4. Eval log — không chỉnh expected sau khi chạy

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

## 5. Commit trail

```text
50cc629 update checkpoint 2
894b286 demo chạy AI lần đầu, chưa bao gồm eval
98fb3c1 update tóm tắt tài liệu chạy open_ai_key
2e06ddf update eval
ca070d8 update tạo câu hỏi
a475f51 update ui/ux hidden sidebar and lll_api
```

## 6. Evidence còn thiếu trước CP5

- Ba willing users có tên và đồng ý test; ưu tiên tuyển từ 31/51 người đã chấm mức quan tâm 4–5.
- Ba lượt test summary với cùng bộ ba câu hỏi trong `spec.md` §8.
- Latency thực tế của happy path trên máy/mạng demo.
- Đối chiếu citation theo trang cho Summary V2.
