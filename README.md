# 🤖 OTP Hub — Telegram Bot

A premium, admin-controlled OTP/service-access Telegram bot built with Python.

## ✨ Features

- **Human Verification** — Captcha + location verification before any interaction
- **User Registration** — Full name, WhatsApp number, service selection
- **Admin Approval Workflow** — Approve/decline/ban users with service assignment
- **Service-Matched OTPs** — Users only see OTPs for their assigned services
- **SMS Parsing Engine** — Automatic classification of SMS by service provider
- **Admin Panel** — Full management inside Telegram (14 sections)
- **Private Channel** — Admin notifications posted to configured channel
- **Broadcast System** — Send messages to filtered user groups
- **Analytics & Audit** — Track every user action for insights

## 🏗️ Architecture

```
bot/                    → Telegram bot (aiogram 3.x)
├── handlers/           → Message & callback handlers
├── handlers/admin/     → Admin-only handlers (guarded)
├── db/                 → SQLAlchemy models & repositories
├── services/           → Business logic (SMS parser, verification)
├── keyboards/          → Inline keyboard builders
├── messages/           → Formatted message templates
├── middlewares/        → DB session, auth, audit, throttle
├── states/             → FSM states for flows
└── utils/              → Validators, time helpers

verification_server/    → Minimal captcha/location verification page
migrations/             → Alembic database migrations
```

## 🚀 Setup

### 1. Prerequisites

- Python 3.11+
- PostgreSQL database
- Telegram Bot Token (from @BotFather)

### 2. Clone & Install

```bash
cd TPBOT
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment

```bash
copy .env.example .env
# Edit .env with your values
```

Required settings:
| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `ADMIN_IDS` | Your Telegram user ID (comma-separated for multiple) |
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port (default: 5432) |
| `DB_NAME` | Database name |
| `DB_USER` | Database username |
| `DB_PASSWORD` | Database password |
| `SMS_API_BASE` | SMS API base URL |
| `VERIFY_BASE_URL` | Public URL for verification page |

### 4. Setup Database

The bot auto-creates tables on first startup. For production migrations:

```bash
# Generate migration
alembic revision --autogenerate -m "initial schema"

# Apply migration
alembic upgrade head
```

### 5. Start the Bot

```bash
python run.py
# or
python -m bot
```

### 6. Bootstrap Admin

Add your Telegram user ID to `ADMIN_IDS` in `.env`. The bot will automatically create admin records on startup.

To find your Telegram ID: message @userinfobot on Telegram.

### 7. Setup Private Channel

1. Create a private Telegram channel/group
2. Add the bot as administrator
3. Get the channel ID (forward a message to @userinfobot)
4. In bot: `/admin` → 📡 Channel → Enter channel ID

### 8. Create Services

1. `/admin` → 🎬 Services → ➕ Create New Service
2. Enter service name, keywords, sender patterns, emoji
3. Example for Netflix:
   - Name: `Netflix`
   - Keywords: `netflix, nflx`
   - Sender patterns: `56161878`
   - Emoji: `🎬`

## 📋 User Flow

1. User sends `/start`
2. Bot shows verification button → opens captcha page
3. User grants location + solves captcha
4. If new user: registration form (name, WhatsApp, services)
5. Admin receives notification in bot + channel
6. Admin approves with service assignment
7. User gets service menu with OTP buttons
8. User taps service → gets latest OTP

## 🛡️ Admin Commands

- `/admin` — Open admin panel
- `/start` — Normal user flow (admins can also be users)

## 📁 Admin Panel Sections

| Section | Description |
|---|---|
| 📊 Dashboard | User counts, OTP stats |
| 👥 All Users | Paginated user list |
| ✅ Verified | Users who passed captcha |
| ⏳ Pending | Awaiting approval |
| ❌ Declined | Rejected users |
| 🚫 Banned | Blocked users |
| 🎬 Services | Create/edit/delete services |
| 📢 Broadcast | Send messages to user groups |
| 📈 Analytics | Detailed action analytics |
| ⚙️ Bot Settings | Welcome/approval/decline messages |
| 💬 Support | Support text configuration |
| 🚫 Ban Message | Custom ban message |
| 📜 Disclaimer | Disclaimer text |
| 📡 Channel | Private channel config |

## 🔧 Production Deployment (VPS)

```bash
# Use systemd service
sudo nano /etc/systemd/system/tpbot.service
```

```ini
[Unit]
Description=TPBOT Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/TPBOT
Environment=PATH=/path/to/TPBOT/venv/bin
ExecStart=/path/to/TPBOT/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable tpbot
sudo systemctl start tpbot
sudo systemctl status tpbot
```

## 📝 License

Private project — all rights reserved.
