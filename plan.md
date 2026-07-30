# Kế hoạch MVP AI Tutor trong 2 giờ

## 1. Mục tiêu

Xây dựng một MVP có thể demo ổn định cho mini-hackathon với luồng chính:

1. Học viên upload slide bài giảng dạng PDF.
2. Hệ thống trích xuất nội dung từ PDF.
3. AI tạo bản tóm tắt ngắn gọn.
4. AI tạo bộ câu hỏi ôn tập kèm đáp án.
5. Người dùng xem kết quả ngay trên giao diện.

> Quyết định sản phẩm: Trong 2 giờ, ưu tiên hoàn thành tốt **một happy path** thay vì xây nhiều chức năng nhưng không ổn định.

---

## 2. Phạm vi MVP

### Must-have

- Upload một file PDF.
- Kiểm tra loại file và giới hạn kích thước.
- Trích xuất text từ PDF.
- Hiển thị trạng thái xử lý.
- Sinh:
  - Tóm tắt bài giảng.
  - 5–10 câu hỏi ôn tập.
  - Đáp án hoặc gợi ý trả lời.
- Cho phép tải kết quả dưới dạng Markdown hoặc copy nội dung.
- Có dữ liệu PDF mẫu để demo dự phòng.

### Nice-to-have nếu còn thời gian

- Chọn số lượng câu hỏi.
- Chọn dạng câu hỏi:
  - Trắc nghiệm.
  - Đúng/sai.
  - Tự luận ngắn.
- Tab “Hỏi đáp” dựa trên nội dung vừa upload.
- Hiển thị số trang và số ký tự đã xử lý.
- Lưu lịch sử trong session.

### Không làm trong MVP 2 giờ

- Đăng nhập, phân quyền.
- Database production.
- Vector database.
- RAG phức tạp.
- OCR toàn bộ slide ảnh.
- Upload PowerPoint trực tiếp.
- Xử lý nhiều file đồng thời.
- Background job, queue, microservice.
- Streaming pipeline phức tạp.
- Mobile app.
- Fine-tuning model.

---

## 3. Tech stack đề xuất

## Phương án được chọn: Python + Streamlit monolith

| Thành phần | Công nghệ | Lý do chọn |
|---|---|---|
| Giao diện | Streamlit | Có sẵn file uploader, button, tabs, spinner; không cần viết React/CSS nhiều |
| Backend | Python trong cùng Streamlit app | Loại bỏ thời gian xây API và kết nối frontend-backend |
| PDF extraction | PyMuPDF | Nhanh, ít dependency, đọc text PDF trực tiếp |
| AI generation | OpenAI API qua Python SDK | Sinh summary và quiz nhanh, chất lượng tốt, hỗ trợ output có cấu trúc |
| Validation | Pydantic | Ép output quiz theo schema, giảm lỗi JSON |
| Config | python-dotenv / Streamlit secrets | Không hard-code API key |
| Storage | `st.session_state` | Đủ cho phiên demo, không cần database |
| Deploy | Streamlit Community Cloud hoặc chạy local | Nhanh nhất cho hackathon |
| Source control | GitHub | Deploy trực tiếp và có lịch sử commit |

### Dependencies tối thiểu

```txt
streamlit
openai
pymupdf
pydantic
python-dotenv
```

### Không nên dùng lúc này

- FastAPI + React/Next.js: kiến trúc đẹp hơn nhưng tăng thời gian wiring, CORS, deploy và debug.
- LangChain/LlamaIndex: hữu ích khi workflow lớn nhưng không cần cho một pipeline hai bước.
- Pinecone/Chroma/Weaviate: chưa cần vector search cho một file PDF nhỏ.
- Celery/Redis/Kafka: quá mức cho demo.
- PostgreSQL/Supabase: chỉ thêm nếu đội đã có sẵn project và cần lưu lịch sử.

---

## 4. Kiến trúc MVP

```text
┌──────────────────────┐
│ Streamlit UI         │
│ - Upload PDF         │
│ - Generate button    │
│ - Summary tab        │
│ - Quiz tab           │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Input validation     │
│ - PDF only           │
│ - File size limit    │
│ - Empty file check   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ PyMuPDF extraction   │
│ - Read page by page  │
│ - Clean whitespace   │
│ - Limit input length │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ OpenAI call          │
│ One structured call: │
│ - summary            │
│ - key points         │
│ - quiz + answers     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Result rendering     │
│ - Summary            │
│ - Questions          │
│ - Download Markdown  │
└──────────────────────┘
```

### Quyết định kỹ thuật quan trọng

Gọi AI **một lần** để sinh cả summary và quiz thay vì hai hoặc ba request riêng.

Lợi ích:

- Giảm latency.
- Giảm chi phí.
- Giảm số điểm có thể lỗi.
- Dễ demo.
- Kết quả summary và quiz dùng chung ngữ cảnh.

---

## 5. Pipeline đầu vào

### Bước 1: Validate file

- Chỉ nhận `.pdf`.
- Giới hạn khoảng 10–20 MB.
- Từ chối file không có nội dung.
- Hiển thị thông báo dễ hiểu.

### Bước 2: Extract text

Pseudo-code:

```python
import pymupdf

def extract_pdf_text(file_bytes: bytes) -> str:
    document = pymupdf.open(stream=file_bytes, filetype="pdf")
    pages = []

    for page_number, page in enumerate(document):
        text = page.get_text("text").strip()
        if text:
            pages.append(
                f"\n--- Trang {page_number + 1} ---\n{text}"
            )

    return "\n".join(pages)
```

### Bước 3: Clean và giới hạn input

- Chuẩn hóa nhiều khoảng trắng.
- Bỏ các dòng lặp quá nhiều nếu có thể.
- Nếu tài liệu quá dài:
  - Chỉ lấy số ký tự/token phù hợp cho demo.
  - Hiển thị cảnh báo “MVP đang xử lý phần nội dung đầu của tài liệu”.
- Không triển khai chunking/map-reduce trừ khi PDF mẫu thực sự quá dài.

### Bước 4: Generate structured output

Schema mong muốn:

```json
{
  "title": "Tên bài học",
  "summary": "Bản tóm tắt",
  "key_points": [
    "Ý chính 1",
    "Ý chính 2"
  ],
  "questions": [
    {
      "type": "multiple_choice",
      "question": "Nội dung câu hỏi",
      "options": ["A", "B", "C", "D"],
      "answer": "B",
      "explanation": "Giải thích ngắn"
    }
  ]
}
```

### Bước 5: Render

Dùng ba khu vực:

- **Tổng quan**: tiêu đề, số trang, số ký tự.
- **Tóm tắt**: summary và key points.
- **Câu hỏi ôn tập**: từng câu hỏi trong expander, đáp án được ẩn bên trong.

---

## 6. Thiết kế prompt

## System prompt

```text
Bạn là AI Tutor hỗ trợ sinh viên ôn tập sau buổi học.

Nhiệm vụ:
1. Chỉ sử dụng thông tin có trong nội dung bài giảng được cung cấp.
2. Viết bản tóm tắt ngắn, rõ ràng, ưu tiên khái niệm và mối quan hệ quan trọng.
3. Tạo câu hỏi kiểm tra khả năng hiểu, không chỉ ghi nhớ từ khóa.
4. Mỗi câu hỏi phải có đáp án và giải thích ngắn.
5. Không bịa thông tin. Nếu nội dung không đủ rõ, ghi chú điều đó.
6. Trả về đúng schema đã yêu cầu.
```

## User prompt

```text
Hãy phân tích nội dung bài giảng dưới đây.

Yêu cầu:
- Tóm tắt trong khoảng 5–10 ý.
- Tạo 8 câu hỏi ôn tập.
- Ưu tiên câu hỏi trắc nghiệm và tự luận ngắn.
- Ngôn ngữ đầu ra: tiếng Việt.
- Câu hỏi phải bám sát nội dung tài liệu.

NỘI DUNG:
{document_text}
```

---

## 7. Cấu trúc source code

```text
ai-tutor-mvp/
├── app.py
├── services/
│   ├── pdf_service.py
│   └── ai_service.py
├── models/
│   └── schemas.py
├── sample/
│   └── demo.pdf
├── .streamlit/
│   └── secrets.toml
├── .env.example
├── requirements.txt
├── README.md
└── plan.md
```

### Phiên bản siêu nhanh

Nếu chỉ có một developer và còn dưới 90 phút:

```text
ai-tutor-mvp/
├── app.py
├── requirements.txt
├── .env
└── sample.pdf
```

Toàn bộ logic có thể để trong `app.py`, sau demo mới refactor.

---

## 8. API/function nội bộ tối thiểu

```python
def validate_pdf(uploaded_file) -> None:
    """Raise a user-friendly error when the uploaded file is invalid."""


def extract_pdf_text(file_bytes: bytes) -> tuple[str, int]:
    """Return extracted text and page count."""


def generate_study_material(
    document_text: str,
    question_count: int = 8,
) -> StudyMaterial:
    """Generate summary, key points, questions and answers."""


def build_markdown(material: StudyMaterial) -> str:
    """Convert generated content to a downloadable Markdown document."""
```

Không cần tạo REST API cho MVP Streamlit.

---

## 9. Data model

```python
from typing import Literal
from pydantic import BaseModel


class Question(BaseModel):
    type: Literal[
        "multiple_choice",
        "true_false",
        "short_answer",
    ]
    question: str
    options: list[str] = []
    answer: str
    explanation: str


class StudyMaterial(BaseModel):
    title: str
    summary: str
    key_points: list[str]
    questions: list[Question]
```

---

## 10. Kế hoạch triển khai trong 2 giờ

## 15:00–15:10 — Chốt scope và setup

- Tạo repository.
- Tạo virtual environment.
- Cài dependencies.
- Tạo `.env` hoặc `secrets.toml`.
- Chuẩn bị một PDF mẫu có text rõ ràng.
- Commit: `chore: initialize ai tutor mvp`.

**Definition of done**

- Chạy được màn hình Streamlit trống.
- API key được đọc từ environment.
- PDF mẫu sẵn sàng.

---

## 15:10–15:30 — Upload và PDF extraction

- Tạo `st.file_uploader`.
- Validate `.pdf`.
- Đọc file bytes.
- Dùng PyMuPDF extract text từng trang.
- Hiển thị:
  - Tên file.
  - Số trang.
  - Số ký tự.
  - Preview 500–1.000 ký tự.
- Xử lý lỗi PDF hỏng hoặc PDF không có text.
- Commit: `feat: upload and extract pdf text`.

**Definition of done**

- Upload PDF mẫu thành công.
- Text hiển thị đúng.
- File lỗi không làm app crash.

---

## 15:30–16:00 — AI generation

- Tạo schema Pydantic.
- Viết system prompt và user prompt.
- Gọi OpenAI API.
- Parse kết quả vào `StudyMaterial`.
- Thêm timeout và `try/except`.
- Lưu kết quả vào `st.session_state`.
- Commit: `feat: generate summary and review questions`.

**Definition of done**

- Một click tạo được summary và ít nhất 5 câu hỏi.
- Output có cấu trúc ổn định.
- Khi API lỗi, UI hiển thị thông báo thay vì stack trace.

---

## 16:00–16:25 — Hoàn thiện UI

- Tạo hai tab:
  - `Tóm tắt`.
  - `Câu hỏi ôn tập`.
- Dùng `st.spinner` khi xử lý.
- Dùng `st.expander` để ẩn đáp án.
- Thêm nút tải Markdown.
- Thêm nút “Tạo lại”.
- Commit: `feat: render study material and export markdown`.

**Definition of done**

- Demo flow liền mạch từ upload đến kết quả.
- Không cần mở terminal trong lúc demo.
- Nội dung dễ đọc và đủ trực quan.

---

## 16:25–16:45 — Test và hardening

Test tối thiểu:

1. PDF bình thường.
2. PDF rỗng hoặc không extract được text.
3. File sai định dạng.
4. API key thiếu.
5. API timeout/error.
6. Nhấn Generate nhiều lần.
7. Refresh ứng dụng.
8. Nội dung tiếng Việt.

Fix ưu tiên:

- Crash.
- JSON parse lỗi.
- Button bị chạy lại ngoài ý muốn.
- Nội dung quá dài.
- Trạng thái cũ còn lại sau khi upload file mới.

Commit: `fix: stabilize demo flow`.

---

## 16:45–17:00 — Chuẩn bị demo

- Chạy lại toàn bộ happy path.
- Chụp screenshot kết quả thành công.
- Lưu sẵn output mẫu trong file Markdown.
- Chuẩn bị video quay màn hình 30–60 giây nếu mạng/API lỗi.
- Viết README gồm cách chạy.
- Tag commit ổn định: `mvp-demo`.

**Definition of done**

- Có một link hoặc lệnh chạy app.
- Có PDF demo cố định.
- Có output dự phòng.
- Có kịch bản thuyết trình 2–3 phút.

---

## 11. Thứ tự cắt giảm khi trễ tiến độ

Nếu sau 30 phút chưa extract được PDF:

1. Dùng file `.txt` hoặc paste text làm input.
2. Giữ PDF upload ở UI nhưng dùng PDF mẫu đã extract sẵn để demo.
3. Không làm OCR.

Nếu sau 60 phút chưa có output AI ổn định:

1. Bỏ Structured Output phức tạp.
2. Yêu cầu model trả Markdown trực tiếp.
3. Chỉ tạo summary + 5 câu hỏi tự luận.
4. Không làm nhiều loại câu hỏi.

Nếu sau 90 phút UI chưa xong:

1. Chỉ dùng một trang.
2. Không dùng tab.
3. Không có download.
4. Hiển thị Markdown trực tiếp.

Nếu deployment gặp lỗi:

1. Demo local.
2. Quay video backup.
3. Không đổi nền tảng deployment sát giờ.

---

## 12. Phương án chatbot Q&A nếu còn 20–30 phút

Không triển khai vector database.

Luồng đơn giản:

```text
Câu hỏi người dùng
        +
Text đã extract từ PDF
        +
Prompt: chỉ trả lời dựa trên tài liệu
        ↓
OpenAI API
        ↓
Câu trả lời + ghi chú trang nếu có
```

Pseudo-code:

```python
def answer_question(document_text: str, question: str) -> str:
    prompt = f"""
    Chỉ trả lời dựa trên tài liệu bên dưới.
    Nếu tài liệu không chứa câu trả lời, hãy nói rõ rằng
    chưa tìm thấy thông tin trong tài liệu.

    TÀI LIỆU:
    {document_text}

    CÂU HỎI:
    {question}
    """
```

Giới hạn:

- Chỉ phù hợp PDF nhỏ.
- Gửi lại toàn bộ text mỗi câu hỏi.
- Chưa tối ưu chi phí.
- Chưa có semantic retrieval.

Với hackathon, giới hạn này có thể chấp nhận được nếu được trình bày rõ là prototype.

---

## 13. Xử lý slide dạng ảnh

PyMuPDF chỉ extract tốt khi PDF có text layer.

Trong MVP:

- Nếu extract được quá ít text, hiển thị:
  - “Tài liệu có thể là slide dạng ảnh; phiên bản MVP chưa hỗ trợ OCR.”
- Cho phép người demo đổi sang PDF mẫu khác.
- Không cài Tesseract/OCR trừ khi tất cả tài liệu bắt buộc là ảnh.

Sau MVP:

- Render từng trang thành ảnh.
- Dùng vision model hoặc OCR.
- Trích xuất theo từng slide.
- Lưu quan hệ giữa đoạn text và số slide.

---

## 14. Error handling

| Trường hợp | Thông báo người dùng | Hành động |
|---|---|---|
| Sai loại file | Chỉ hỗ trợ PDF | Không xử lý |
| File quá lớn | File vượt giới hạn MVP | Yêu cầu file nhỏ hơn |
| Không có text | PDF có thể là dạng ảnh | Dừng và gợi ý PDF khác |
| API key thiếu | Hệ thống chưa được cấu hình | Không gọi API |
| API timeout | AI đang phản hồi chậm | Cho phép thử lại |
| Parse output lỗi | Không thể chuẩn hóa kết quả | Retry một lần hoặc fallback Markdown |
| Tài liệu quá dài | Chỉ xử lý một phần tài liệu | Cắt input và cảnh báo |

Không hiển thị traceback hoặc API key lên giao diện.

---

## 15. Tiêu chí nghiệm thu MVP

MVP được coi là hoàn thành khi:

- [ ] Người dùng upload được một PDF có text.
- [ ] Hệ thống extract được nội dung trong dưới vài giây với PDF mẫu.
- [ ] Người dùng nhấn một nút để bắt đầu.
- [ ] Hệ thống sinh được bản tóm tắt tiếng Việt.
- [ ] Hệ thống sinh được ít nhất 5 câu hỏi có đáp án.
- [ ] UI không crash khi input không hợp lệ.
- [ ] Có PDF demo và output backup.
- [ ] Toàn bộ happy path có thể trình diễn trong dưới 2 phút.

---

## 16. Chỉ số sản phẩm cho hackathon

### North-star demo metric

**Thời gian từ lúc upload slide đến lúc có tài liệu ôn tập sử dụng được.**

Mục tiêu demo:

- Dưới 30–60 giây tùy model và độ dài PDF.

### Chỉ số phụ

- Tỷ lệ câu hỏi bám sát nội dung.
- Tỷ lệ output parse thành công.
- Số thao tác từ upload đến kết quả.
- Mức độ hữu ích do người dùng tự đánh giá.
- Thời gian tiết kiệm so với tự đọc và tự tạo câu hỏi.

---

## 17. Kịch bản demo 2–3 phút

### Bước 1 — Nêu pain point

“Sau mỗi buổi học, sinh viên có slide nhưng mất nhiều thời gian đọc lại, xác định ý chính và tự nghĩ câu hỏi ôn tập.”

### Bước 2 — Upload

Upload một PDF mẫu khoảng 5–15 trang.

### Bước 3 — Generate

Nhấn “Tạo tài liệu ôn tập”.

Trong lúc chờ, giải thích pipeline:

```text
PDF → extract text → AI hiểu nội dung → summary + quiz
```

### Bước 4 — Trình bày kết quả

- Mở phần tóm tắt.
- Chỉ ra key points.
- Mở hai câu hỏi.
- Hiện đáp án và giải thích.

### Bước 5 — Chốt giá trị

“Thay vì chỉ chat với tài liệu, MVP biến bài giảng thành một gói ôn tập có cấu trúc ngay sau buổi học.”

### Bước 6 — Roadmap

- Q&A có trích nguồn theo slide.
- Cá nhân hóa mức độ khó.
- Theo dõi câu trả lời sai.
- Spaced repetition.
- Xử lý audio bài giảng và đồng bộ với slide.

---

## 18. Roadmap sau hackathon

### V1

- FastAPI backend.
- Next.js frontend.
- PostgreSQL/Supabase.
- Object storage.
- Authentication.
- Async job.
- Lưu lesson và quiz.

### V2

- Chunking.
- Embeddings.
- Vector database.
- RAG có citation theo slide.
- OCR/vision cho slide ảnh.
- Upload PPTX và audio.
- Speech-to-text.

### V3

- Question difficulty.
- Adaptive quiz.
- Knowledge tracing.
- Spaced repetition.
- Dashboard tiến độ.
- Teacher review workflow.

---

## 19. Phân công nếu có 2–3 người

### Hai người

**Developer A**

- Streamlit UI.
- File upload.
- Rendering.
- Download.

**Developer B**

- PDF extraction.
- Prompt.
- AI call.
- Schema và error handling.

### Ba người

**Developer A:** UI và demo flow.  
**Developer B:** AI pipeline.  
**Developer C:** test, deployment, README, slide pitch và backup demo.

Không để nhiều người cùng sửa `app.py` trong 60 phút cuối.

---

## 20. Checklist trước khi trình bày

- [ ] API key hoạt động.
- [ ] Không commit `.env`.
- [ ] PDF mẫu có text layer.
- [ ] Internet ổn định.
- [ ] App đã warm-up ít nhất một lần.
- [ ] Output không chứa hallucination rõ ràng.
- [ ] Có screenshot/video backup.
- [ ] Có output Markdown backup.
- [ ] Font tiếng Việt hiển thị đúng.
- [ ] Không demo bằng file quá dài.
- [ ] Tắt log chứa dữ liệu nhạy cảm.
- [ ] Git đang ở commit ổn định.

---

## 21. Kết luận kỹ thuật

Đối với deadline 2 giờ, lựa chọn tốt nhất là:

```text
Streamlit
+ Python
+ PyMuPDF
+ OpenAI API
+ Pydantic
+ session_state
```

Chỉ xây luồng:

```text
Upload PDF → Tóm tắt → Câu hỏi ôn tập → Đáp án
```

Không tách frontend/backend, không database, không vector DB và không OCR trong bản MVP đầu tiên.

Đây là phạm vi nhỏ nhất vừa thể hiện được năng lực AI/backend, vừa tạo ra trải nghiệm sản phẩm hoàn chỉnh và đủ rõ để thuyết trình tại mini-hackathon.
