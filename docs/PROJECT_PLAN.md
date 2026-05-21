Human-in-the-Loop Multi-Agent Japanese Document Processing System

1. Mục tiêu và bài toán cần giải quyết
1.1 Bối cảnh
Trong nhiều doanh nghiệp Nhật Bản hiện nay, các quy trình vận hành vẫn phụ thuộc rất lớn vào:
- Tài liệu PDF
- Invoice
- Hợp đồng
- Form nội bộ
- Fax
- Tài liệu scan
- Tài liệu legacy

Việc xử lý các tài liệu này thường được thực hiện thủ công bởi nhân viên văn phòng thông qua:
- Nhập liệu
- Kiểm tra hóa đơn
- Xác minh hợp đồng
- Approval workflow

Điều này dẫn đến:
- Chi phí vận hành cao
- Workflow chậm
- Sai sót nhập liệu
- Khó mở rộng hệ thống

1.2 Vấn đề của OCR tiếng Nhật hiện nay
Các hệ thống OCR truyền thống thường được tối ưu cho:
- Tiếng Anh
- Tài liệu Latin alphabet
- Layout đơn giản

Trong khi đó, tài liệu doanh nghiệp Nhật Bản thường có:
- Kanji phức tạp
- Chữ viết dọc
- Bảng biểu dày đặc
- Tài liệu scan chất lượng thấp
- Font legacy
- Layout không cố định

Các vấn đề phổ biến gồm:
- OCR nhận sai Kanji
- Không xử lý tốt vertical text
- Sai bounding boxes
- OCR fail với noisy scan
- Không hỗ trợ explainability
- Không học từ feedback của người dùng

1.3 Mục tiêu dự án
Dự án đề xuất xây dựng:
Human-in-the-Loop Multi-Agent Japanese Document Processing System
Mục tiêu chính:
- Xử lý tài liệu doanh nghiệp tiếng Nhật
- Cải thiện OCR thông qua human feedback
- Trích xuất dữ liệu có cấu trúc
- Hỗ trợ workflow Multi-Agent
- Hỗ trợ explainable AI
- Triển khai thành hệ thống web thực tế

1.4 Kết quả mong muốn
Hệ thống có khả năng:
- Upload PDF hoặc scan document tiếng Nhật
- OCR tiếng Nhật
- Extract dữ liệu quan trọng
- Validate dữ liệu
- Generate summary
- Export JSON/YAML/CSV
- Hỗ trợ correction workflow
- Cải thiện OCR theo thời gian

2. Kế hoạch triển khai (Master Schedule)
Week 1 — Research & System Design
Bách — Team Leader & System Architect
Công việc
- Research Multi-Agent workflow
- Research Human-in-the-loop systems
- Thiết kế system architecture
- Setup FastAPI backend
- Setup Docker environment
- Thiết kế API contract giữa các modules
Deliverables
- Overall architecture
- API design
- Docker environment

Gia Hân — OCR & Vision Engineer
Công việc
- Research Japanese OCR
- Research vertical text recognition
- Benchmark PaddleOCR Japanese
- Dataset preprocessing
- Build OCR baseline
Deliverables
- OCR baseline
- OCR evaluation notebook
- Dataset preprocessing pipeline

Khang — LLM & Extraction Engineer
Công việc
- Research LayoutLMv3
- Research structured extraction
- Research JSON generation workflow
- Build extraction baseline
- Prompt engineering
Deliverables
- Extraction prototype
- JSON schema
- LLM prompting baseline

Mỹ Hân — Frontend & Human Feedback Engineer
Công việc
- Research enterprise dashboard UI
- Research OCR correction workflow
- Setup NextJS frontend
- Setup TailwindCSS
- Build upload UI prototype
- Chuẩn bị thesis outline
- Research evaluation metrics
Deliverables
- Frontend skeleton
- Upload interface
- Dashboard mockup
- Thesis outline
- Evaluation plan

Week 2 — OCR & Extraction Module
Bách — Team Leader & System Architect
Công việc
- Research LangGraph orchestration
- Implement Multi-Agent backend
- Build orchestration APIs
- Connect OCR ↔ Extraction pipeline
Deliverables
- Multi-Agent backend
- Agent orchestration pipeline

Gia Hân — OCR & Vision Engineer
Công việc
- Research OCR error patterns
- Fine-tune OCR
- Improve vertical text handling
- OCR confidence scoring
- OCR benchmarking
Deliverables
- Improved OCR model
- OCR evaluation report

Khang — LLM & Extraction Engineer
Công việc
- Research layout-aware extraction
- Implement Extraction Agent
- Build JSON/YAML export
- Connect OCR output → LLM pipeline
- Structured output validation
Deliverables
- Extraction Agent
- Structured output pipeline

Mỹ Hân — Frontend & Human Feedback Engineer
Công việc
- Build OCR visualization UI
- Build extracted field editor
- API integration
- Build dashboard prototype
- Viết evaluation section
- Chuẩn bị workflow diagrams
Deliverables
- OCR viewer
- Editable extraction interface
- Dashboard prototype
- Evaluation documentation

Week 3 — Multi-Agent & Human Feedback
Bách — Team Leader & System Architect
Công việc
- Research agent memory systems
- Implement correction memory
- Build workflow state management
- Optimize agent orchestration
Deliverables
- Correction memory system
- Workflow engine

Gia Hân — OCR & Vision Engineer
Công việc
- Research OCR refinement strategies
- Implement OCR correction pipeline
- Build OCR feedback refinement
- Analyze OCR improvement after feedback
Deliverables
- OCR refinement module
- OCR feedback evaluation

Khang — LLM & Extraction Engineer
Công việc
- Research explainable AI
- Implement Validation Agent
- Implement Summary Agent
- Build confidence scoring system
- Structured reasoning evaluation
Deliverables
- Validation Agent
- Summary generation module

Mỹ Hân — Frontend & Human Feedback Engineer
Công việc
- Build feedback interface
- Build approval workflow UI
- Build analytics dashboard
- User workflow evaluation
- Visualization for OCR metrics
- Viết thesis documentation
Deliverables
- Human feedback UI
- Approval system
- Analytics dashboard
- Evaluation figures
- Thesis documentation draft

Week 4 — Deployment & Evaluation
Bách — Team Leader & System Architect
Công việc
- Backend optimization
- Docker deployment
- Final system integration
- Deployment testing
- Final presentation preparation
Deliverables
- Deployable system
- Final architecture documentation

Gia Hân — OCR & Vision Engineer
Công việc
- OCR benchmarking
- Japanese OCR evaluation
- Error analysis
- OCR performance optimization
- Generate evaluation charts
Deliverables
- OCR benchmark report
- OCR error analysis

Khang — LLM & Extraction Engineer
Công việc
- Evaluate extraction accuracy
- Optimize extraction pipeline
- Improve validation logic
- Build final evaluation scripts
- Generate structured reasoning report
Deliverables
- Extraction benchmark
- Validation benchmark
- Structured reasoning report

Mỹ Hân — Frontend & Human Feedback Engineer
Công việc
- Final UI polish
- UX testing
- User workflow analysis
- Build final visualization dashboard
- Finalize thesis documentation
- Prepare presentation materials
Deliverables
- Final UI
- Demo dashboard
- Thesis evaluation section
- Presentation assets

3. Kiến trúc và Luồng vận hành (Architecture & Workflow)

3.1 System Architecture

3.2 Workflow
Step 1 — Upload Document
Người dùng upload:
- PDF
- Invoice
- Scan document
- Japanese forms

Step 2 — OCR Agent
OCR Agent:
- Detect text boxes
- OCR tiếng Nhật
- Xử lý vertical text
- Generate OCR output

Step 3 — Extraction Agent
Extraction Agent:
- Extract enterprise information
- Convert text thành structured data
- Generate JSON/YAML/CSV output
Ví dụ:
{
  "invoice_id": "INV001",
  "company": "株式会社ABC",
  "amount": 120000
}

Step 4 — Validation Agent
Validation Agent:
- Validate OCR output
- Detect anomalies
- Calculate confidence score
- Verify field consistency
Step 5 — Human Feedback
Người dùng có thể:
- Sửa lỗi OCR
- Chỉnh sửa dữ liệu
- Approve workflow
Step 6 — Correction Memory
Hệ thống lưu:
- Feedback history
- OCR mistakes
- Correction patterns
Mục tiêu:
- Adaptive OCR refinement
- Improve future predictions
Step 7 — Structured Export
Output:
- JSON
- YAML
- CSV
- Summary report

4. Công nghệ (Tech Stack)
4.1 AI / Machine Learning
Component | Technology
OCR | PaddleOCR Japanese
Document Understanding | LayoutLMv3
LLM | Phi-3 Mini / Qwen2.5
Embedding | BGE-small

4.2 Backend
Component | Technology
API Server | FastAPI
Multi-Agent Orchestration | LangGraph
Database | PostgreSQL
Vector Search | FAISS

4.3 Frontend
Component | Technology
Frontend | NextJS
UI | TailwindCSS
Visualization | Chart.js

4.4 Deployment
Component | Technology
Containerization | Docker
GPU Environment | CUDA
Model Serving | HuggingFace / vLLM

5. Phân công nhân sự (Roles & Responsibilities)
Team gồm 4 thành viên:
- Nguyễn Xuân Bách (Leader)
- Tăng Gia Hân
- Tăng Mỹ Hân
- Lữ Huy Khang

6. Chi tiết từng module trong kiến trúc
6.1 OCR Module
Chức năng
- OCR tiếng Nhật
- Detect text boxes
- Xử lý vertical text
- Generate OCR output
Input
- PDF
- Image
- Scanned documents
Output
- Extracted text
- Coordinates
- Confidence score

6.2 Extraction Module
Chức năng
- Convert text thành structured data
- Extract enterprise information
- Generate JSON/YAML/CSV output

6.3 Validation Module
Chức năng
- Validate OCR output
- Detect anomalies
- Calculate confidence score
- Verify field consistency

6.4 Human Feedback Module
Chức năng
- Cho phép user sửa lỗi
- Approve workflow
- Lưu correction history
- Improve OCR refinement

6.5 Correction Memory Module
Chức năng
- Lưu feedback history
- Analyze OCR mistakes
- Support adaptive refinement
- Improve future predictions

6.6 Export Module
Chức năng
- Export JSON
- Export YAML
- Export CSV
- Generate summary report

7. Dataset và Evaluation
7.1 Japanese OCR Datasets
- Kuzushiji Dataset
- NDL Dataset
- Japanese Receipt OCR
- Synthetic Japanese Forms

7.2 Enterprise Document Datasets
- FUNSD
- SROIE
- DocVQA

7.3 Evaluation Metrics
OCR Metrics
- Character Accuracy
- Word Accuracy
- Character Error Rate (CER)
Human Feedback Metrics
- Correction Reduction Rate
- Human Approval Rate
- OCR Improvement after Feedback
Multi-Agent Metrics
- Extraction Precision
- Agent Agreement Score
- Structured Output Accuracy



