# AI Dev Team

AI Dev Team là một hệ thống **multi-agent local-first** dùng Python để mô phỏng một team phát triển phần mềm nhỏ gồm:

- PM
- Architect
- Developer
- QA
- Lead

Hệ thống nhận một task đầu vào, tự đi qua các bước phân tích, thiết kế, generate code, kiểm tra lỗi, build validation, retry khi fail, và lưu run history vào MongoDB để tái sử dụng cho các lần chạy sau.

---

## 1. Mục tiêu hệ thống

Workflow chính:

1. Phân tích task
2. Viết PRD
3. Thiết kế kiến trúc
4. Generate project React + Vite
5. QA theo requirement
6. Chạy build validation thật
7. Retry loop nếu còn lỗi
8. Lưu run history vào MongoDB

---

## 2. Technical stack

### Runtime
- Python 3.11+

### LLM inference
- Ollama local

### Model routing
- **PM / Architect / Lead** -> `gemma3:4b`
- **Developer / QA** -> `qwen3:8b`

### Output project
- React + Vite

### Run history / memory
- MongoDB

---

## 3. Kiến trúc tổng quan

```text
Task
→ Load similar run history from MongoDB
→ PM
→ Architect
→ Developer
→ QA
→ Executor
→ Rule-based Release Gate
→ Lead
→ Retry or Done
→ Save final run to MongoDB
```

### Retry loop
- `MAX_LOOP = 3`

### Required files tối thiểu cho React project
- `package.json`
- `index.html`
- `src/main.jsx`
- `src/App.jsx`

Nếu Developer trả JSON invalid hoặc empty thì orchestrator sẽ đánh lỗi và retry.

---

## 4. Project structure

```text
.
├── agents/
│   ├── architect.py
│   ├── developer.py
│   ├── lead.py
│   ├── pm.py
│   └── qa.py
├── core/
│   ├── db.py
│   ├── executor.py
│   ├── file_manager.py
│   ├── llm.py
│   ├── memory.py
│   └── orchestrator.py
├── scripts/
│   ├── clear_runs.py
│   ├── list_runs.py
│   └── show_run.py
├── output_project/
├── main.py
├── README.md
├── requirements.txt
└── pyproject.toml
```

---

## 5. Setup và run source

### Yêu cầu môi trường

Cần cài sẵn:
- Python 3.11+
- Node.js 18+
- npm
- Ollama
- MongoDB

Kiểm tra nhanh:

```bash
python3 --version
node -v
npm -v
ollama --version
```

### 1. Clone source

```bash
git clone <your-repo-url>
cd <your-repo-folder>
```

### 2. Tạo virtual environment

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Cài Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Pull model từ Ollama

```bash
ollama pull gemma3:4b
ollama pull qwen3:8b
```

### 5. Chạy MongoDB local

Nếu dùng Docker:

```bash
docker run -d \
  --name ai-dev-team-mongo \
  -p 27017:27017 \
  -v mongo_data:/data/db \
  mongo:8
```

### 6. Biến môi trường

Tạo file `.env` thủ công hoặc export trực tiếp:

```bash
export MONGO_URI="mongodb://localhost:27017"
export MONGO_DB_NAME="ai_dev_team"
export MONGO_RUNS_COLLECTION="runs"
export OLLAMA_HOST="http://127.0.0.1:11434"
```

### 7. Run source

#### Chạy bằng task string trực tiếp

```bash
python main.py "Build a simple React todo app with add, delete, and filter"
```

#### Hoặc dùng file task

Tạo file `task.txt`:

```txt
Build a simple React todo app with add, delete, and filter
```

Sau đó chạy:

```bash
python main.py --task-file task.txt
```

### 8. Run kèm output JSON

```bash
python main.py "Build a dashboard with sidebar and cards" --json
```

### 9. Save result ra file

```bash
python main.py "Build a pricing page" --save-result result.json
```

### 10. Kiểm tra output project

Sau khi run thành công, source React sẽ được ghi vào thư mục:

```bash
output_project/
```

Ví dụ kiểm tra file:

```bash
ls output_project
find output_project -maxdepth 3 -type f
```

### 11. Build thử project generated

```bash
cd output_project
npm install
npm run build
```

Lưu ý: trong flow chính, `core/executor.py` cũng sẽ tự chạy build validation.

### 12. Exit code

- `0`: DONE
- `2`: chưa DONE, cần retry/fix thêm
- `1`: lỗi runtime hoặc input

---

## 6. Run history trong MongoDB

MongoDB được dùng để lưu **run history / debug records / query records**.

Mỗi run sẽ có các field chính như:

- `run_id`
- `task`
- `final_decision`
- `release_status`
- `severity`
- `loop_count`
- `execution_error`
- `qa_detail`
- `history`
- `summary`
- `created_at`

### Script inspect

List run gần nhất:

```bash
python scripts/list_runs.py
```

Xem chi tiết 1 run:

```bash
python scripts/show_run.py <run_id>
```

Xóa toàn bộ run history:

```bash
python scripts/clear_runs.py
```

---

## 7. Agent model routing

### PM
- model: `gemma3:4b`

### Architect
- model: `gemma3:4b`

### Developer
- model: `qwen3:8b`

### QA
- model: `qwen3:8b`

### Lead
- model: `gemma3:4b`

---

## 8. Release gate

Release decision là **rule-based**, không phụ thuộc hoàn toàn vào LLM.

### DONE khi
- không có `execution_error`
- không có `structural_bugs`
- không có `functional_bugs`
- không có `prd_gaps`
- chỉ còn `ui_gaps` nhỏ hoặc không còn lỗi

### RETRY khi
- build fail
- thiếu file hoặc import sai
- logic sai
- thiếu feature theo PRD

### Severity hiện dùng
- `BLOCKER`
- `MINOR`
- `NONE`

Nguồn sự thật là:
- `classify_release_status(context)` trong `core/orchestrator.py`

---

## 9. Troubleshooting

### `zsh: command not found: python`
Thử:

```bash
python3 main.py "Build a todo app"
```

### `ollama: command not found`
Ollama chưa được cài hoặc chưa vào PATH.

### Model chưa tồn tại
Pull lại:

```bash
ollama pull gemma3:4b
ollama pull qwen3:8b
```

### Build fail ở output project
Kiểm tra:
- thiếu file bắt buộc
- import path sai
- `package.json` không hợp lệ
- dependency thiếu hoặc version sai

### Mongo chưa chạy
Kiểm tra MongoDB đã start ở `mongodb://localhost:27017` chưa.

---

## 10. Hướng phát triển tiếp theo

Một số next steps hợp lý:
- thêm schema validator cứng cho Developer / QA / Lead
- improve retry strategy
- chuẩn hóa logging
- bổ sung `.env.example`
- viết test cho release gate
- thêm query theo task / severity / status trong scripts Mongo

---

## 11. Tóm tắt ngắn

AI Dev Team hiện là một local multi-agent workflow:

- PM / Architect / Lead dùng `gemma3:4b`
- Developer / QA dùng `qwen3:8b`
- output project là React + Vite
- run history dùng MongoDB
- build được validate thật bằng executor
- release quyết định bằng hard rule trong orchestrator
