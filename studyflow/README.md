# StudyFlow AI Tutor MVP

MVP Streamlit biến PDF bài giảng thành bản tóm tắt hoặc bộ câu hỏi ôn tập bằng hai luồng OpenAI độc lập.

## Tính năng

- Upload và kiểm tra PDF tối đa 20 MB.
- Trích xuất text và tín hiệu hình ảnh theo từng trang bằng PyMuPDF.
- OCR cục bộ bằng Tesseract khi máy đã cài; thiếu Tesseract không làm app lỗi.
- Chỉ gọi OpenAI Vision cho tối đa các trang scan/sơ đồ/nhiều ảnh được rule-base chọn.
- Cache kết quả Vision để Summary và Quiz dùng chung, không trả phí phân tích ảnh hai lần.
- Tạo Summary V2 gồm tổng quan, mục tiêu học tập, khái niệm, quy trình, điểm dễ nhầm và takeaway.
- Dẫn nguồn theo trang cho từng phần của summary và từng câu hỏi.
- Tạo 5–10 câu hỏi bằng OpenAI Structured Outputs.
- Xem đáp án trong expander.
- Tải toàn bộ kết quả dưới dạng Markdown.
- Dữ liệu demo dự phòng khi chưa có API key hoặc mạng không ổn định.

## Cài đặt

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Điền `OPENAI_API_KEY` trong `.env`. Có thể đổi `OPENAI_MODEL`; mặc định là `gpt-5.6-sol`.

Các cấu hình pipeline hình ảnh đã có trong `.env.example`. `VISION_IMAGE_DETAIL=low` ưu tiên tốc độ/chi phí; tăng lên `high` hoặc `original` khi slide có chữ và biểu đồ rất nhỏ. Kết quả Vision được lưu trong `var/visual_cache` theo hash PDF, số trang, model và detail.

## Chạy demo

```powershell
streamlit run app.py
```

Mở `http://localhost:8501`. Nếu chưa có API key, chọn **Dùng dữ liệu demo** trong sidebar để kiểm tra toàn bộ giao diện kết quả.

## Chạy test

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
python -m unittest discover -s tests -p "test_*.py" -v
```

## Phạm vi

Đây là MVP hackathon: hỗ trợ PDF có text layer hoặc slide dạng ảnh, chưa có database, vector search, PPTX, authentication hoặc background jobs. Xem `../plan.md` để biết phạm vi và roadmap.
