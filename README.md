# StudyFlow AI
LINK SLIDE TRÌNH BÀY: https://canva.link/87egwdq4rg9mzja
Chatbot hỗ trợ học từ slide: đọc PDF/PPTX, tạo AI Notes, AI Summary, AI Flashcards, AI Quiz và trả lời có dẫn chiếu theo từng slide.

## Trạng thái hiện tại

- UI prototype chạy bằng Streamlit.
- Backend đã được refactor sang modular monolith trong `starter_v0/src/studyflow`.
- Domain models và dependency ports đã sẵn sàng.
- Parser, retrieval, generation và API chưa được implement.
- Research agent cũ được bảo toàn trong `starter_v0/legacy/research_agent`.

## Chạy UI

```bash
cd starter_v0
python -m pip install -r requirements.txt
streamlit run app.py
```

Mở `http://localhost:8501`.

## Tài liệu kiến trúc

Xem `starter_v0/docs/ARCHITECTURE.md` để đọc keep/drop map, dependency boundaries, data flow và thứ tự triển khai backend.
