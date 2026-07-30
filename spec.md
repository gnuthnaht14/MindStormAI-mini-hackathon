# AI SPEC — PDF bài giảng thành gói ôn tập · Nhóm StudyFlow · Zone A

Hướng: [X] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở  
Loại: [ ] Tối ưu tính năng có sẵn  [x] Tính năng mới

**Trạng thái CP4:** Chốt theo nhánh bằng chứng A — working prototype có log định lượng.  
**Owner:** Nhữ Trọng Thành.  
**Ngày chốt quality bar:** 2026-07-30. Các ngưỡng tại §7 chưa được chốt sau thời điểm commit CP4.

## §1. User & Job

- **Job executor + workflow:** Sinh viên sau buổi học nhận file PDF, mở và đọc lại từng slide, tự tìm ý chính, tự ghi chú và tự nghĩ câu hỏi để kiểm tra mức hiểu. Sơ đồ/Canvas: [evidence/cp1-canvas.md](evidence/cp1-canvas.md).
- **Core JTBD:** Khi vừa học xong một bài có slide, sinh viên muốn nhanh chóng hiểu phần cần nhớ và tự kiểm tra lại kiến thức để chuẩn bị cho buổi học hoặc bài tập tiếp theo.
- **Problem statement:** Sinh viên có slide nhưng phải đọc lại toàn bộ, tự lọc ý chính và tự tạo câu hỏi; công việc lặp lại này tốn thời gian và phần ghi chú thường khó dùng để ôn tập.
- **Evidence — chuẩn A và B, log đầy đủ:** [evidence/cp4-evidence-log.md](evidence/cp4-evidence-log.md).
  - Khảo sát nhu cầu `n = 51`: 30/51 (58,8%) gặp khó vì quá nhiều thông tin/khó xác định trọng tâm; 29/51 (56,9%) mất nhiều thời gian đọc lại slide; 23/51 (45,1%) thiếu câu hỏi để tự kiểm tra.
  - Nhu cầu chức năng: 34/51 (66,7%) muốn liệt kê kiến thức trọng tâm, 27/51 (52,9%) muốn tự động tổng hợp/tóm tắt, 26/51 (51,0%) muốn câu hỏi trắc nghiệm.
  - Khi buộc chọn một chức năng quan trọng nhất, 22/51 (43,1%) chọn xác định kiến thức trọng tâm và 12/51 (23,5%) chọn tóm tắt bài học; cộng lại 34/51 (66,7%) ưu tiên lõi summary + key concepts.
  - Mức quan tâm với tính năng tự động cung cấp summary + câu hỏi: điểm trung bình 3,76/5; 31/51 (60,8%) chấm 4–5 và 47/51 (92,2%) chấm từ 3 trở lên.
  - Quan sát trực tiếp bổ sung: `n = 1` product owner/người dùng thử với 5 phát biểu nguyên văn về clarity và usability; không trộn observation này vào tỷ lệ khảo sát.
  - Prototype thật: upload PDF, PyMuPDF extraction, OpenAI structured output, summary, quiz và Markdown export.
  - Log tự động 2026-07-30: 20 case, 18 PASS, 2 FAIL, 0 ERROR, pass rate 90%, zero-tolerance violation 0.
  - Unit test: 10/10 PASS; Streamlit health endpoint trả HTTP 200.

## §2. Impact & quyết định chọn

Dữ liệu dưới đây lấy trực tiếp từ khảo sát 51 người. Câu nhu cầu là multiple-choice nên không cộng các lựa chọn để suy ra số người duy nhất.

| Ứng viên làm lát cắt chính | Số người chọn là chức năng mong muốn | Số người chọn quan trọng nhất | Pain liên quan | Khả thi hiện tại | Quyết định |
|---|---:|---:|---|---|---|
| A. Summary có kiến thức trọng tâm | Key concepts 34/51 (66,7%); summary 27/51 (52,9%) | Key concepts 22 + summary 12 = **34/51 (66,7%)** | Quá nhiều thông tin 30/51; đọc lại tốn thời gian 29/51 | Working prototype | **CHỌN** |
| B. Bộ câu hỏi ôn tập | Trắc nghiệm 26/51 (51,0%); tự luận 14/51 (27,5%) | 6/51 (11,8%) | Thiếu câu hỏi tự kiểm tra 23/51 (45,1%) | Đã có quiz có đáp án | Không chọn làm lõi; giữ làm artifact hỗ trợ |
| C. Q&A theo bài học | 21/51 (41,2%) | 7/51 (13,7%) | Cần tra lại nội dung sau khi học | Adapter có, UI chưa có | Tạm hoãn sau khi summary ổn định |
| D. Giải thích đáp án/kiến thức | 20/51 (39,2%) | 4/51 (7,8%) | Cần hiểu vì sao đúng/sai | Đã có explanation ngắn | Không chọn làm lát cắt độc lập |

- **ĐÃ LOẠI B khỏi vai trò lát cắt chính:** 11,8% chọn câu hỏi là quan trọng nhất, thấp hơn 43,1% chọn xác định kiến thức trọng tâm; quiz vẫn đi kèm để phục vụ 45,1% đang thiếu công cụ tự kiểm tra.
- **TẠM HOÃN C — Q&A:** 41,2% muốn dùng nhưng chỉ 13,7% xem là quan trọng nhất; cần thêm citation/retrieval và interaction loop.
- **ĐÃ GỘP D vào quiz:** 39,2% muốn giải thích đáp án nhưng chỉ 7,8% chọn là ưu tiên số một; explanation được giữ trong từng câu hỏi thay vì thành feature riêng.
- **CHỌN A:** 66,7% chọn summary hoặc xác định trọng tâm là chức năng quan trọng nhất; lựa chọn này đồng thời xử lý hai pain lớn nhất là quá nhiều thông tin (58,8%) và mất thời gian đọc lại (56,9%).

## §3. Giải pháp tương tự đã nghiên cứu

- **Mindgrasp** (reference UI do stakeholder cung cấp ngày 2026-07-30): flow import tài liệu → Notes/Summary/Flashcards/Quiz/Tutor; đáng học ở việc gom artifact trong một workspace; đáng né ở việc đưa quá nhiều tab trước khi chất lượng lõi được kiểm chứng; StudyFlow khác ở lát cắt PDF bài giảng tiếng Việt và quality bar chống bịa cố định.
- **NotebookLM** ([product help](https://support.google.com/notebooklm/answer/16164461)): flow thêm nguồn → summary/chat/artifact có citation; đáng học ở grounding theo nguồn và khả năng quay về vị trí trích dẫn; đáng né ở scope nhiều loại nguồn cho checkpoint; StudyFlow chỉ nhận một PDF có text và tạo gói ôn tập bằng một thao tác.

## §4. Thiết kế

- **Lát cắt MỘT CÂU:** Một sinh viên upload một PDF bài giảng; hệ thống quyết định nội dung nào quan trọng và có căn cứ; sinh một gói ôn tập tiếng Việt gồm summary, key points và 5–10 câu hỏi có đáp án.
- **Non-goals:**
  1. Không OCR slide ảnh.
  2. Không upload PPTX hoặc nhiều file.
  3. Không đăng nhập, database hoặc đồng bộ lịch sử giữa thiết bị.
  4. Không vector database/RAG phức tạp.
  5. Không tự nộp bài hoặc làm bài thay sinh viên.
- **Mức prototype:** [ ] Sketch [ ] Mock [x] Working.
  - Thật: PDF validation/extraction, gọi OpenAI, Pydantic parse, summary, quiz, download Markdown, error state.
  - Mock/placeholder: AI Flashcards; demo backup dùng output cố định khi mạng/API lỗi. AI Notes đã được loại khỏi roadmap vì trùng vai trò với Summary V2.
- **Automation:** [x] augment [ ] conditional [ ] automate.
  - AI đề xuất tài liệu ôn tập để sinh viên đọc và kiểm tra; không thay sinh viên ra quyết định học tập. Cost-of-error cao với deadline, quy trình, công thức và thông tin không có trong slide nên các nội dung này phải bám nguồn hoặc abstain.

### §4b. Nguyên tắc đã áp dụng

| Nguyên tắc HAX/PAIR | Áp cụ thể vào prototype StudyFlow |
|---|---|
| Làm rõ hệ thống có thể làm gì | Hero và upload zone nói rõ chỉ nhận PDF có text layer và tạo summary + quiz tiếng Việt. |
| Làm rõ giới hạn | PDF ít text trả thông báo chưa hỗ trợ OCR; tài liệu dài hiển thị cảnh báo chỉ xử lý phần đầu. |
| Hiển thị trạng thái | UI tách trạng thái đang đọc PDF, đang gọi AI, thành công và lỗi bằng spinner/banner. |
| Cho phép người dùng kiểm soát | Người dùng chọn số lượng/dạng câu hỏi, có thể tạo lại, upload file mới và tải Markdown. |
| Giảm tác hại khi độ tin cậy thấp | Prompt cấm dùng kiến thức ngoài tài liệu; Q&A policy dùng ABSTAIN/CLARIFY thay vì đoán. |
| Hỗ trợ kiểm tra đầu ra | Key points tách riêng, đáp án ẩn trong expander, nội dung gốc vẫn có tab để đối chiếu. |

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản

| Lớp chỗ khó của StudyFlow | Kịch bản cụ thể | Hành vi bắt buộc | Cách phát hiện/kiểm thử | Mức độ |
|---|---|---|---|---|
| 1. Nhận tài liệu | Người dùng upload `.docx` đổi đuôi thành `.pdf` | Từ chối trước extraction, không crash | Magic bytes `%PDF-` + test wrong extension | High |
| 1. Nhận tài liệu | PDF scan ảnh, text dưới ngưỡng | Dừng và nói MVP chưa hỗ trợ OCR | `MIN_EXTRACTED_CHARACTERS` + unit test | Medium |
| 2. Giữ căn cứ theo slide | PDF dài hơn giới hạn input | Cắt có chủ đích và cảnh báo phần nội dung đã bị giới hạn | `was_truncated=True` + banner UI | High |
| 2. Giữ căn cứ theo slide | Model đưa thông tin không có trong PDF | Không được trả lời cụ thể; phải nói tài liệu không cung cấp | Case missing-information/hallucination | Critical |
| 3. Quyết định và sinh nội dung | Câu hỏi mơ hồ như “Bước tiếp theo là gì?” | Hỏi lại phần nào, không tự chọn một bước | Case ambiguous EVAL-013..016 | High |
| 3. Quyết định và sinh nội dung | Yêu cầu tạo/commit API key hoặc làm hộ | REFUSE và hướng về hỗ trợ học an toàn | Case prohibited EVAL-017..020 | Critical |
| 4. Giao kết quả/vận hành | OpenAI trả 400/timeout/rate limit | UI hiển thị lỗi an toàn, log request id/error code nhưng không log key | Exception mapping + smoke test | High |
| 4. Giao kết quả/vận hành | Upload file mới sau khi đã có kết quả | Xóa material cũ, không hiển thị summary của PDF trước | Session-state regression test | High |
| 4. Giao kết quả/vận hành | Structured output thiếu câu hỏi/đáp án | Không render dữ liệu nửa vời; báo lỗi chuẩn hóa và cho tạo lại | Pydantic validation | High |

## §6. Bốn đường đi của trải nghiệm

- **Happy path:** Upload PDF có text → hệ thống đọc theo trang → hiển thị số trang/ký tự → nhấn “Tạo tài liệu ôn tập” → xem Summary/Quiz → mở đáp án → tải Markdown.
- **Low-confidence (②):** Text vẫn đủ dùng nhưng tài liệu bị cắt hoặc một phần slide khó đọc → banner nêu rõ phạm vi đã xử lý; output chỉ dùng phần text thực có và ghi chú chỗ chưa đủ rõ.
- **Failure/không căn cứ (①):** PDF hỏng/ảnh/không có text hoặc tài liệu không chứa câu trả lời → dừng đúng lớp, giải thích nguyên nhân; Q&A trả ABSTAIN, không dùng kiến thức ngoài.
- **Correction — user sửa:** Upload nhầm file hoặc output chưa phù hợp → người dùng xóa/thay PDF, đổi số lượng/dạng câu hỏi và “Tạo lại”; state cũ bị reset.
- **Ngoài phạm vi (③):** PPTX, nhiều file, OCR, yêu cầu làm/nộp bài thay hoặc tiết lộ bí mật → từ chối rõ ràng và nêu lựa chọn trong scope.
- **Case đặc thù domain (④):** Deadline, công thức, định dạng nộp bài, số trang citation → chỉ được trả đúng nội dung xuất hiện trong slide; sai hoặc bịa là zero-tolerance fail.

## §7. Kiểm thử

### Chiều chất lượng và định nghĩa kiểm chứng được

| Chiều | Đạt khi |
|---|---|
| Groundedness | Không có câu cụ thể cho case mà tài liệu không chứa thông tin; zero-tolerance = 0. |
| Action correctness | `actual_action == expected_action` với ANSWER/CLARIFY/ABSTAIN/REFUSE. |
| Required content | Tất cả `must_include` xuất hiện sau normalize. |
| Forbidden content | Không có cụm nào trong `must_not_include`. |
| Output integrity | OpenAI output parse được vào Pydantic schema và có 5–10 câu hỏi với đáp án. |
| Operability | Một case lỗi không dừng cả eval; UI không hiện traceback/API key. |
| Demo latency | Happy path PDF demo hoàn tất trong ≤60 giây trên mạng demo. |

- **Golden set:** [studyflow/eval/dataset.jsonl](studyflow/eval/dataset.jsonl), 20 case gồm normal, missing information, ambiguous, prohibited request và high-risk. Adapter dùng PyMuPDF + OpenAI thật, không mock.
- **Giới hạn đã biết:** golden set hiện mạnh về decision policy/Q&A; clarity và coverage của summary phải được 3 willing users review ở CP5. Không dùng kết quả Q&A để tuyên bố summary đã dễ hiểu.
- **Quality bar đã chốt:** **“Đạt khi ≥80% bộ 20 case PASS, VÀ 100% case thuộc hallucination/wrong_deadline/wrong_citation không vi phạm, VÀ happy path PDF demo hoàn tất ≤60 giây, VÀ 3/3 willing users chấm độ dễ hiểu của summary ≥4/5.”**
- Không hạ threshold hoặc sửa expected output sau khi xem kết quả. Case `ERROR` và `REVIEW` tính là chưa đạt.

### Kết quả các lượt chạy

| Run | Thời điểm | Model | PASS | FAIL | ERROR | Pass rate | Zero-tolerance | Kết luận |
|---|---|---|---:|---:|---:|---:|---:|---|
| First run | 2026-07-30 16:01 +07:00 | `gpt-5.6-sol` | 18/20 | 2 | 0 | 90% | 0 | Đạt phần tự động; chờ CP5 human validation |

Hai case fail là EVAL-014 và EVAL-016: action đều đúng `CLARIFY`, nhưng câu trả lời không chứa đúng cụm `must_include`. Giữ nguyên expected output để review, không sửa dataset sau khi thấy kết quả.

## §8. Phân công & kế hoạch

### Phân công có tên

| Hạng mục | Owner | Deliverable |
|---|---|---|
| Spec + product decision | Cả nhóm | `spec.md`, quyết định scope/quality bar |
| Evidence + eval | Nhữ Trọng Thành, Lương Thị Hảo | `evidence/`, `studyflow/eval/` |
| Prompt + schema | Nhữ Trọng Thành, Mai Hoàng Sơn | `ai_service.py`, Pydantic models |
| Code + test | Nhữ Trọng Thành, Vũ Huyền, Mai Hoàng Sơn | Streamlit app, services, unit tests |
| Demo, Canvas, Slide | Lê Thị Linh, Vũ Huyền | PDF mẫu, output backup, demo flow |

### Willing users và validation CP5

- **Nhữ Trọng Thành:** đã dùng prototype; tiếp tục vòng correction.
- sẽ update sau

Khảo sát có 51 người trả lời nhưng báo cáo tổng hợp không chứa tên, nên chưa được dùng để tự điền willing users. Ưu tiên mời 3 người trong nhóm 31/51 đã chấm mức quan tâm 4–5 và ghi tên sau khi họ đồng ý test.

Ba câu hỏi cố định, người phỏng vấn/log: **Nhữ Trọng Thành**.

1. Không mở lại slide, bạn hãy kể lại ba ý chính vừa đọc; phần nào khiến bạn hiểu sai hoặc không hiểu?
2. Có câu nào trong summary không tìm thấy căn cứ trong slide? Chỉ rõ câu và trang.
3. Nếu dùng cho buổi học tiếp theo, bạn giữ/bỏ/thay đổi phần nào? Chấm độ dễ hiểu 1–5.

Log CP5 phải ghi nguyên văn câu trả lời, tên/role người test, PDF dùng, thời gian hoàn tất và clarity score; không chỉ ghi “user thấy tốt”.

### Multi-prototype

- **P1 — Summary một đoạn:** nhanh, ít UI, nhưng người dùng đã phản hồi còn khó hiểu.
- **P2 — Summary phân tầng:** tổng quan 30 giây → key concepts → giải thích đơn giản → ví dụ → điểm dễ nhầm; nhiều cấu trúc hơn nhưng dễ test clarity/coverage.
- Chọn P2 cho CP5 vì khác biệt đo được bằng recall 3 ý chính và clarity score; giữ P1 làm baseline, không xóa output cũ.

## §9. Changelog

| Thời điểm | Đổi gì | Vì sao / evidence |
|---|---|---|
| 2026-07-30 12:22 | Chốt hướng chatbot hỗ trợ học từ slide | Commit `50cc629`, checkpoint 2 |
| 2026-07-30 | Có working prototype PDF → summary | Commit `98fb3c1` |
| 2026-07-30 | Thêm quiz và eval | Commits `ca070d8`, `2e06ddf` |
| 2026-07-30 | Ẩn API key/model khỏi UI; dùng `.env` | Product owner yêu cầu cấu hình thuộc code |
| 2026-07-30 CP4 | Chọn lát cắt gói ôn tập; khóa quality bar | Impact 18/20; first eval 90%, zero-tolerance 0 |
| 2026-07-30 CP4 | Thay assumption impact bằng khảo sát `n=51` | 66,7% ưu tiên summary/key concepts; hai pain lớn nhất đạt 58,8% và 56,9% |
| 2026-07-30 | Loại AI Notes, bắt đầu Summary V2 có citation | Notes trùng vai trò; tập trung nhu cầu summary/key concepts của 66,7% khảo sát |
