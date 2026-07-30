# StudyFlow AI
LINK SLIDE TRÌNH BÀY: https://canva.link/87egwdq4rg9mzja
Trợ lý hỗ trợ học từ slide: đọc PDF, tạo AI Summary có cấu trúc và dẫn nguồn, sau đó sinh bộ câu hỏi ôn tập có đáp án.

## Trạng thái hiện tại

- UI và backend MVP chạy bằng Streamlit trong `studyflow/`.
- PyMuPDF parser và OpenAI structured generation đã hoạt động.
- Summary V2 và quiz có citation theo trang.
- Flashcards và retrieval-grounded AI Tutor nằm trong roadmap tiếp theo.

## Chạy UI

```bash
cd studyflow
python -m pip install -r requirements.txt
streamlit run app.py
```

Mở `http://localhost:8501`.

## Tài liệu kiến trúc

Xem `studyflow/docs/ARCHITECTURE.md` để đọc dependency boundaries, data flow và thứ tự triển khai backend.
