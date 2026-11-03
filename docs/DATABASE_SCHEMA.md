# Database Schema (SQL Server)

- Database: `DevTeamAI` (ứng dụng), `DevTeamAI_Test` (pytest). Tạo bằng `scripts/create_db.sql`.
- Bảng tạo bằng Alembic: `backend/alembic/versions/`.
  - `1f87fbd3a806` – initial schema (12 bảng)
  - `a060f447a1ae` – seed 7 agent + quyền + `app_settings.limits`

## Quy ước

| Hạng mục | Quy ước |
|---|---|
| Khóa chính | `BIGINT IDENTITY` |
| Văn bản | `NVARCHAR(n)` / `NVARCHAR(MAX)` (collation instance là Latin1 → bắt buộc Unicode) |
| Thời gian | `DATETIME2`, UTC, mặc định `SYSUTCDATETIME()` |
| JSON | `NVARCHAR(MAX)` + `CHECK (ISJSON(col) = 1)`. **Lưu ý:** `ISJSON` chỉ chấp nhận object/array, không nhận số/chuỗi đơn |
| Enum | `VARCHAR(30)` + `CHECK IN (...)` (SQL Server không có enum) |
| Tên constraint | `pk_<table>`, `fk_<table>_<col>_<ref>`, `uq_<table>_<cols>`, `ck_<table>_<name>`, `ix_<table>_<cols>` |
| Xóa dây chuyền | Chỉ `projects → workflow_runs → bảng con` dùng `ON DELETE CASCADE`. FK phụ (`task_id`, `agent_id`, `approval_id`) dùng NO ACTION vì SQL Server cấm nhiều đường cascade |

## Sơ đồ quan hệ

```
projects 1─* workflow_runs 1─* tasks *─1 agents 1─* agent_permissions
                     │            │  └─* task_dependencies (task_id, depends_on_task_id)
                     ├─* artifacts ─(task_id)
                     ├─* approvals ─(task_id)
                     ├─* execution_events ─(task_id)
                     ├─* command_executions ─(task_id, approval_id)
                     └─* llm_usage ─(task_id, agent_id)
app_settings (key/value)
```

## Bảng

### projects
| Cột | Kiểu | Ghi chú |
|---|---|---|
| id | BIGINT PK | |
| name | NVARCHAR(200) UNIQUE | |
| description | NVARCHAR(MAX) NULL | |
| status | VARCHAR(30) | `active` \| `archived` |
| workspace_dir | NVARCHAR(100) UNIQUE | Tên thư mục dưới `WORKSPACES_ROOT`, không phải đường dẫn tuyệt đối |
| created_at, updated_at | DATETIME2 | |

### agents
`id, code (UNIQUE), name, role_description, model, max_output_tokens, is_enabled, instructions NULL, extra_params JSON NULL, created_at, updated_at`

### agent_permissions
`id, agent_id → agents (CASCADE), permission` – UNIQUE(agent_id, permission). Giá trị: `plan.create`, `task.assign`, `fs.read`, `fs.write:<area>` (`docs|backend|frontend|tests`), `cmd.run`.

### workflow_runs
`id, project_id → projects (CASCADE), request_text, status (pending|planning|running|waiting_approval|completed|failed|cancelled), budget_usd, total_input_tokens, total_output_tokens, total_cost_usd, summary, error, started_at, finished_at, created_at, updated_at`

### tasks
`id, run_id → workflow_runs (CASCADE), agent_id → agents, task_key (UNIQUE theo run), title, description, status (pending|ready|running|waiting_approval|completed|failed|skipped), attempt, max_attempts, input_data JSON, output_data JSON, error, started_at, finished_at, created_at, updated_at`

### task_dependencies
`task_id → tasks (CASCADE), depends_on_task_id → tasks` – PK kép, CHECK không tự phụ thuộc.

### artifacts
`id, run_id (CASCADE), task_id NULL, kind (requirements|design|source_file|test_report|review...), name, content NULL, file_path NULL (tương đối với workspace), created_at`

### approvals
`id, run_id (CASCADE), task_id NULL, kind, title, payload JSON, status (pending|approved|rejected), decision_note, decided_at, created_at` – index (status, created_at).

### execution_events
`id, run_id (CASCADE), task_id NULL, event_type, message, data JSON, created_at` – timeline append-only, nguồn của WebSocket và Execution History.

### command_executions
`id, run_id (CASCADE), task_id NULL, approval_id NULL, command, args JSON, cwd, status (pending|running|succeeded|failed|timed_out|rejected), exit_code, stdout, stderr, duration_ms, created_at, finished_at`

### llm_usage
`id, run_id (CASCADE), task_id NULL, agent_id, model, input_tokens, cached_input_tokens, output_tokens, request_count, cost_usd DECIMAL(12,6), latency_ms, created_at`

### app_settings
`key NVARCHAR(100) PK, value JSON (object), updated_at`. Seed: `limits = {max_task_attempts: 3, max_fix_iterations: 3, command_timeout_seconds: 120, default_run_budget_usd: 2.0}`. Bảng giá model sẽ thêm ở tuần 2 theo bảng giá chính thức của OpenAI.

## Kiểm chứng

- `tests/test_schema.py`: JSON round-trip, cascade xóa project, CHECK ISJSON, CHECK không tự phụ thuộc.
- Migration đã chạy `upgrade → downgrade → upgrade` thành công trên SQL Server 2022.
