# StudyFlow backend architecture

## Mục tiêu của lần refactor

Hệ thống mới là một modular monolith: đủ rõ ràng để phát triển nhanh, nhưng các boundary cho parser, LLM, retrieval và storage vẫn có thể tách thành service riêng khi cần scale.

## Keep / replace / remove

| Thành phần cũ | Quyết định | Cách dùng trong hệ thống mới |
|---|---|---|
| `providers/` | Giữ ý tưởng, viết adapter mới | Tiếp tục chuẩn hóa OpenAI, OpenRouter, Anthropic và Gemini; bổ sung structured output, multimodal input, token usage và retry. |
| `chat.run_model_tool_loop` | Giữ trace contract, thay orchestration | Không dùng tool loop tự do cho mọi tác vụ. Mỗi use case có pipeline rõ ràng; AI Tutor mới có thể dùng bounded tools. |
| Transcript và tool events | Giữ, đổi schema | Trở thành audit event cho ingest, retrieval, generation và chat; không lưu raw file hay secret. |
| `versioning.py` | Giữ ý tưởng | Version prompt, parser, chunker và schema output thay vì chỉ hash prompt/tool YAML. |
| `run_eval.py` | Giữ phương pháp, viết eval mới | Đánh giá groundedness, citation, coverage, flashcard quality và quiz validity. |
| `clarify` | Giữ behavior | Chuyển thành application state `needs_user_input`, không phải một tool LLM tùy ý. |
| `fetch`, `format` | Refactor một phần | `format` trở thành renderer/serializer; `fetch` chỉ còn nếu sản phẩm hỗ trợ import URL. |
| Twitter, Telegram, policy, arXiv tools | Bỏ khỏi runtime mới | Không liên quan đến slide-learning; được lưu trong `legacy/research_agent`. |
| Research prompt và eval datasets | Bỏ khỏi runtime mới | Lưu làm lịch sử, không import vào package mới. |
| Streamlit prototype | Giữ tạm thời | Chỉ là presentation layer; không đặt business logic, parser hay LLM call trong `app.py`. |

## Cấu trúc mới

```text
starter_v0/
├── app.py                         # UI prototype hiện tại
├── pyproject.toml
├── requirements.txt
├── docs/
│   └── ARCHITECTURE.md
├── src/studyflow/
│   ├── config.py                  # Runtime configuration
│   ├── domain/
│   │   ├── models.py              # Session, document, slide, artifact, citation
│   │   └── ports.py               # LLM, parser, retrieval, repository contracts
│   ├── application/
│   │   └── commands.py            # Input DTO cho các use case
│   ├── infrastructure/
│   │   ├── document_parsers/      # PDF, PPTX, OCR adapters
│   │   ├── llm/                   # Provider adapters
│   │   ├── persistence/           # Local/Postgres/object storage
│   │   └── retrieval/             # Chunking, embeddings, vector index
│   ├── presentation/
│   │   ├── api/                   # FastAPI routes/schemas trong phase sau
│   │   └── streamlit/             # UI adapters trong phase sau
│   └── prompts/                    # Prompt templates có version
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evals/
└── legacy/research_agent/         # Toàn bộ lab research agent cũ
```

## Luồng dữ liệu mục tiêu

### 1. Import slide

1. Presentation nhận file PDF/PPTX và metadata.
2. `IngestDocument` lưu file qua `FileStorage`.
3. `DocumentParser` tạo `SlideDocument` gồm text, notes và asset theo từng trang.
4. Chunker tạo các `SourceChunk` có `slide_indexes` để giữ citation chính xác.
5. `RetrievalIndex` index chunk; `DocumentRepository` cập nhật trạng thái `ready`.

### 2. AI Notes / Summary / Flashcards / Quiz

1. Presentation gửi `GenerateArtifactCommand` với session, document, loại artifact và scope slide.
2. Application service lấy đúng chunks, dựng prompt theo artifact type rồi gọi `LLMClient` với output schema bắt buộc.
3. Output validator loại câu hỏi thiếu đáp án, flashcard trùng lặp hoặc citation không tồn tại.
4. `ArtifactRepository` lưu artifact và prompt/model/schema version.

### 3. AI Tutor

1. `AskTutorCommand` chứa câu hỏi và lịch sử hội thoại giới hạn.
2. Retriever lấy chunks liên quan trong document hiện tại.
3. LLM chỉ trả lời trên context đã lấy và phải gắn citation theo slide.
4. Nếu evidence không đủ, assistant nói rõ thay vì tự suy đoán.

## Boundary quan trọng

- UI không đọc file, chunk text, gọi provider hay ghi transcript trực tiếp.
- Domain không import Streamlit, FastAPI, SDK provider hoặc database client.
- Mỗi artifact dùng schema riêng; không dùng một chuỗi text chung cho summary, flashcard và quiz.
- Citation luôn tham chiếu `document_id` và `slide_indexes`, không chỉ là URL/text tự do.
- File gốc và extracted text có lifecycle riêng; không đưa toàn bộ document vào chat history.
- Research agent cũ là legacy read-only; code mới không import ngược từ `legacy`.

## Thứ tự triển khai đề xuất

1. PDF/PPTX parser + local repositories.
2. Ingestion pipeline + slide/chunk viewer data.
3. Summary và notes với structured output.
4. Retrieval-grounded AI Tutor.
5. Flashcards và quiz + validation.
6. FastAPI boundary, background jobs và persistence production.
7. Bộ eval mới và observability dashboard.
