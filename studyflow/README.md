# StudyFlow AI Tutor MVP

MVP Streamlit biến PDF bài giảng thành bản tóm tắt hoặc bộ câu hỏi ôn tập bằng hai luồng OpenAI độc lập.

## Tính năng

- Upload và kiểm tra PDF tối đa 20 MB.
- Trích xuất text theo từng trang bằng PyMuPDF.
- Cảnh báo PDF dạng ảnh hoặc tài liệu bị cắt do quá dài.
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

Đây là MVP hackathon: một PDF có text layer, không database, vector search, OCR, PPTX, authentication hoặc background jobs. Xem `../plan.md` để biết phạm vi và roadmap.
