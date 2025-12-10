# Media Agency Operations Platform Blueprint

## Assumptions
- Deployment on a single LAN-accessible server (Linux) with Docker and docker-compose available; host has a mounted NAS path at `/mnt/agency-media` with adequate free space.
- Internal users access via browser on the local network; no external client portal yet.
- Telegram bot token and webhook URL are available; outbound internet access exists for Telegram API and optional AI API calls.
- Timezone is set at the server level; dates/times stored in UTC with UI-localized presentation.

## Recommended Stack (self-hosted, low-code first)
- **Application layer:** [NocoBase](https://nocobase.com/) for data modeling, RBAC, Kanban/table/calendar views, file attachments, and REST API.
- **Database:** PostgreSQL (single instance used by NocoBase).
- **Automations/Integrations:** n8n for Telegram, reminders, and AI workflows (can call NocoBase REST/GraphQL).
- **File storage:** Local/NAS directory mounted into NocoBase and n8n containers (e.g., `/mnt/agency-media`).
- **Reverse proxy:** Caddy/NGINX for LAN-friendly hostnames + TLS if desired.

## High-Level Architecture
- **NocoBase** hosts core data models, UI (kanban/table/calendar), authentication, and role-based permissions. Provides REST endpoints consumed by n8n.
- **n8n** acts as the automation hub: Telegram bot webhook, scheduled reminders, cross-department handoffs, AI summaries, workload-based auto-assign.
- **PostgreSQL** stores structured data; **NAS** stores large media referenced via attachment fields.
- **Optional AI** (OpenAI-compatible API) called from n8n to generate summaries/assistant responses.

```
[Users] ⇄ Browser ⇄ NocoBase (RBAC, UI, REST) ⇄ PostgreSQL
                                  ⇵
                             NAS / Local Storage
                                  ⇵
                                n8n (webhooks, schedulers, Telegram, AI)
```

## Core Data Model (ERD-style overview)
- **User** (managed by NocoBase)
  - Fields: name, email/login, role (enum: Admin, PM, Editor, Designer, Marketer, Finance, FutureClient), department (enum), is_active.
  - Relations: assigned_tasks (Task.assignee), comments, finance visibility via role.
- **Client**
  - Fields: name, brand_name, logo (file), status (enum: active/paused/past), notes, contract_type (enum), package_description, social_profiles (json), telegram_chat_id, contact_people (json array of {name,email,phone,telegram}).
  - Relations: tasks (1→M), invoices (1→M), expenses (optional 1→M), messages (1→M), files (attachments or folders).
- **Task**
  - Fields: title, description (rich text), department (enum: Recording, Editing, Design, Marketing, ClientComms, Finance), status (enum per department), assignee (User), client (Client), due_date, publish_date, priority (enum), tags (array), needs_client_feedback (bool), platform (enum/lookup), attachments (files), created_at/updated_at.
  - Relations: comments/messages (1→M), depends_on (optional self M2M for prerequisites).
- **Comment / Message**
  - Fields: body (rich text), type (enum: internal_comment, telegram_inbound, telegram_outbound), created_by (User nullable for inbound), client (Client), task (Task nullable), telegram_message_id (optional), attachments (files), direction (enum inbound/outbound), timestamp.
  - Relations: belongs to Client; optionally Task.
- **Invoice**
  - Fields: client (Client), amount, currency, description/period, issue_date, due_date, status (Draft/Sent/Paid/Overdue), paid_date, payment_method, notes.
- **Expense**
  - Fields: date, category (enum), amount, currency, vendor, description, client (optional), attachment (receipt).

### Status Pipelines (task.status values)
- Recording: To Do → Scheduled → In Progress → Footage Uploaded → Done
- Editing: To Do → In Progress → Review → Approved → Exported/Done
- Design: To Do → In Progress → Review → Done
- Marketing: Brief → Content Ready → Scheduled → Posted/Done
- Client Communication: New Request → Waiting on Client → Client Responded → Closed
- Finance/Admin: To Do → In Progress → Done

## Roles & Permissions (summary)
- **Admin/Owner:** full CRUD on all entities, user management, automation configs.
- **Project Manager:** read/write all tasks/clients/messages; cannot delete invoices/expenses; view finance dashboard (read-only).
- **Editor/Designer/Marketer (Department Users):**
  - Read/write tasks in their department or assigned to them.
  - View related client basic info and chat; cannot view finance data.
  - Comment on tasks; trigger status changes.
- **Finance:** full CRUD on invoices/expenses; read-only on clients/tasks/messages for context; cannot change task assignments.
- **Future Client (optional):** restricted portal (not enabled now) to view own tasks/messages/files.

Permissions implemented via NocoBase roles + collection-level policies (filter by department/assignee) and view-level access for Finance module.

## UI Modules / Screens
- **Dashboard:** KPIs (tasks by status, overdue counts, revenue/expense snapshot), personal "My Tasks" list.
- **Department Boards:** Kanban per department filtered by `department` with drag/drop; quick filters by client, assignee, due date.
- **Task Detail:** rich description, attachments, status/department switcher, assignee, dates, tags, comments/messages thread, client context, toggle `needs_client_feedback`.
- **Client Directory:** table of clients with status filters.
- **Client Profile:** header (brand, contacts, quick Telegram/phone links); tabs for Overview (deliverables progress), Tasks (list/kanban), Calendar (publish_date), Chat (messages), Files, Finance (invoices/payments).
- **Global Calendar:** publish_date items with color-coding by client or platform; drag/drop to change date; filters by client/platform/department.
- **Finance:** invoices table, expenses table, finance dashboard (revenue, expenses, profit, overdue list). Visible to Admin/Finance; PM read-only summary.
- **Messages/Chat View:** chronological feed per client; compose message -> triggers Telegram via n8n webhook.
- **Notifications Panel:** mentions, new assignments, inbound client messages, due date reminders.

## Automation Flows (n8n)
1. **Cross-department handoff (Recording → Editing)**
   - Trigger: NocoBase webhook on Task update where `department=Recording` and `status=Footage Uploaded`.
   - Actions: set `department=Editing`, `status=To Do`; optionally set `assignee` to round-robin editor; log comment.
2. **Client notification via Telegram**
   - Trigger: Task status changes to `Ready for Client`/`Approved` or boolean `needs_client_feedback` toggled true with new attachment.
   - Actions: build message `🎬 {task.title} ready for review` with link/attachment; send via Telegram Bot API using client's `telegram_chat_id`; store outbound Message record; notify assignee/PM.
3. **Reminder/Overdue alert**
   - Trigger: Scheduled (hourly/daily). Query tasks where `due_date <= now + 1 day` and `status` not in done states.
   - Actions: send in-app notification + optional email/Telegram to assignee + PM; mark task with "At Risk" tag.
4. **Inbound Telegram → Message record**
   - Trigger: Telegram bot webhook to n8n.
   - Actions: map `chat_id` to Client; create Message record (type=telegram_inbound, direction=inbound) and optionally attach media; if message references a task id/hash, link to task; send internal notification.
5. **AI Monthly Client Summary (optional)**
   - Trigger: Cron at month-end.
   - Actions: query completed tasks per client; feed structured data to AI API; store generated summary text in a ClientSummary collection and post to PM.
6. **Auto-assignment (optional)**
   - Trigger: Task created without assignee.
   - Actions: query active users in the department; compute workload (# active tasks); assign to least-loaded user; add comment noting auto-assignment.

## Data Stored for Messages (Telegram integration)
- client_id, task_id (nullable), body text, attachments (file path/URL), telegram_message_id, chat_id, direction (inbound/outbound), timestamp, created_by (for outbound), status (sent/delivered/fail), raw_payload (json for diagnostics).

## Deployment & Configuration (docker-compose excerpt)
```yaml
version: '3.9'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: agency
      POSTGRES_USER: agency
      POSTGRES_PASSWORD: agency_pw
    volumes:
      - pgdata:/var/lib/postgresql/data
  nocobase:
    image: nocobase/nocobase:latest
    depends_on: [postgres]
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_DATABASE: agency
      DB_USER: agency
      DB_PASSWORD: agency_pw
      STORAGE_TYPE: local
      STORAGE_PATH: /mnt/agency-media
    volumes:
      - /mnt/agency-media:/mnt/agency-media
    ports:
      - "13000:13000"
  n8n:
    image: n8nio/n8n:latest
    depends_on: [postgres]
    environment:
      DB_TYPE: postgresdb
      DB_POSTGRESDB_HOST: postgres
      DB_POSTGRESDB_DATABASE: n8n
      DB_POSTGRESDB_USER: agency
      DB_POSTGRESDB_PASSWORD: agency_pw
      N8N_HOST: n8n.local
      N8N_PORT: 5678
      N8N_PROTOCOL: http
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
    volumes:
      - /mnt/agency-media:/mnt/agency-media
    ports:
      - "5678:5678"
volumes:
  pgdata:
```

### Environment Variables
- `TELEGRAM_BOT_TOKEN`: Bot token for Telegram.
- `TELEGRAM_WEBHOOK_URL`: Public webhook URL (can use reverse proxy + HTTPS).
- `OPENAI_API_KEY` (optional): For summaries/assistant.
- `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD`: protect n8n UI.

## Implementation Plan (Phases)
1. **Phase 1 – Core Data & Boards**
   - Deploy stack, create collections (User/Client/Task/Message/Invoice/Expense), seed enums and roles.
   - Configure Kanban views per department and global task list filters; enable file storage to NAS.
2. **Phase 2 – Client Experience & Calendar**
   - Build Client Profile views (tabs), global & client-filtered calendars (publish_date), deliverables progress summaries.
3. **Phase 3 – Finance & Telegram**
   - Configure Finance tables and dashboard; restrict permissions.
   - Implement Telegram bot via n8n (outbound notifications + inbound message logging), compose view.
4. **Phase 4 – Automations & AI**
   - Add cross-department handoff, reminders, auto-assignment.
   - Implement monthly AI summaries and optional "Ask the system" assistant powered by n8n webhook + AI.

## "Ask the System" Assistant (design)
- **Interface:** In-app form or command in NocoBase calling n8n webhook.
- **Input:** Natural language query + user context.
- **Flow:** n8n parses intent via AI (few-shot prompt with schema), queries NocoBase REST (e.g., tasks filtered by client/status/due), formats concise answer, returns to UI.
- **Outputs:** Markdown text plus optional links to records; logged as Message of type `assistant` linked to user.

## Operational Notes
- Set up regular PostgreSQL backups and NAS snapshots.
- Use role-based API tokens per automation; audit logs enabled in NocoBase.
- Large media transfers should use NAS paths; tasks store references to avoid DB bloat.

