<div align="center">
  <br>
  <h1>🛡️ Raffbot-priv</h1>
  <p><strong>Solo Leveling — Discord Multi-Purpose Bot</strong></p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/discord.py-2.4%2B-5865F2?logo=discord&logoColor=white" alt="discord.py">
    <img src="https://img.shields.io/badge/Gemini%20AI-2.5%20Flash-4285F4?logo=google&logoColor=white" alt="Gemini AI">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  </p>
  <br>
</div>

---

## 👁️ Overview

**Raffbot-priv** — bot Discord multifungsi bertema **Solo Leveling** dengan sistem RPG journal, auto rank promotion, welcome/goodbye cards, PDF tools, AI nutrition analysis, reminder system, dan chat XP leaderboard.

> *"Arise, Hunter. Your journey begins here."*

---

## ✨ Features

### ⚔️ Solo Leveling RPG Journal
| Command | Description |
|---|---|
| `/start` | Buka Menu Utama HUD dengan kartu Hunter |
| `/log` | Catat quest harian (manual / form popup) |
| `/rank` | Status Window — lihat rank & XP |
| `/myrank` | Ringkasan profil & role Hunter |
| `/agenda` | Papan Quest Board harian |
| `/today` / `/yesterday` | Lihat log hari ini / kemarin |
| `/date <YYYY-MM-DD>` | Lihat log tanggal tertentu |
| `/search <keyword>` | Cari catatan jurnal |
| `/all` | Arsip semua tanggal |
| `/stats` | Kartu statistik lengkap |
| `/clear` | Hapus log hari ini (interaktif) |
| `/del <id>` | Hapus log by ID (autocomplete) |

### 👑 Hunter Rank System
- 🛡️ **E-Rank** — 0+ Quest
- ⚔️ **D-Rank** — 10+ Quest
- 🏹 **C-Rank** — 30+ Quest
- 🔮 **B-Rank** — 75+ Quest
- ⚡ **A-Rank** — 150+ Quest
- 🔥 **S-Rank** — 300+ Quest
- 🌌 **National Level** — 500+ Quest
- 👑 **God Mode** — 1000+ Quest *(Owner only)*

Role otomatis sync saat naik rank — dengan icon role khusus!

### 🖼️ Welcome & Goodbye System
- Custom welcome/goodbye channel
- Pesan kustom dengan `{user}`, `{name}`, `{server}`
- Welcome card bergambar avatar member
- `/welcome channel`, `/welcome message`, `/goodbye channel`, `/goodbye message`

### 📄 PDF Tools & Document Converter
Upload file `.pdf` → menu interaktif:
- 🗜️ **Compress** — perkecil ukuran PDF
- 📑 **To Images** — ekstrak halaman ke gambar
- 🔒 **Lock** — enkripsi PDF dengan password
- 🔓 **Unlock** — buka PDF terproteksi
- 🏷️ **Watermark** — tambah watermark teks
- ✂️ **Split** — pisah PDF per halaman
- 📝 **Word (DOCX)** — konversi PDF ke Word
- 📊 **Excel (XLSX)** — konversi PDF ke Excel

Upload `.docx`, `.xlsx`, `.pptx`, `.png`/`.jpg` → konversi otomatis ke PDF.

### 🤖 AI Nutritionist — Gemini 2.5 Flash
- 📸 Upload foto makanan → analisis kalori, protein, karbohidrat, lemak
- 📝 Simpan hasil analisis langsung ke jurnal harian
- 🧠 Tag `@Raffbot-priv` untuk chat AI dalam Bahasa Indonesia

### ⏰ Reminder System
| Command | Description |
|---|---|
| `/remind <HH:MM> <pesan>` | Reminder harian (DM) |
| `/remindat <YYYY-MM-DD> <HH:MM> <pesan>` | Reminder sekali |
| `/reminders` | Daftar reminder aktif |
| `/unremind <id>` | Hapus reminder (autocomplete) |

### 💬 Chat XP & Leaderboard
- Dapatkan XP dari setiap pesan di server
- Level up otomatis dengan role chat rank
- `/chatrank` — lihat XP & level
- `/leaderboard` — Top 10 server

### 🛠️ Utility
| Command | Description |
|---|---|
| `/projects` | Lihat repositori GitHub Pidzzzz |
| `/addrole <member> <role>` | Beri role (Admin/Owner) |
| `/removerole <member> <role>` | Hapus role (Admin/Owner) |
| `!restart` | Restart bot (Owner only) |
| `!clear_logs` | Bersihkan semua log (Owner only) |

---

## 🚀 Installation

### Prerequisites
- Python 3.11+
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- (Optional) Gemini API Key untuk AI fitur

### Setup

```bash
# Clone repository
git clone https://github.com/Pidzzzz/raffbot-discord.git
cd raffbot-discord

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
```

Edit `.env`:
```env
# Discord Bot Token (required)
DISCORD_TOKEN=your_discord_bot_token_here

# Google Gemini API Key (optional, for AI features)
GEMINI_API_KEY=your_gemini_api_key_here
```

### Run
```bash
python bot.py
```

---

## ⚙️ Configuration

### Bot Intents Required
Enable in [Discord Developer Portal](https://discord.com/developers/applications):
- ✅ **Message Content Intent**
- ✅ **Server Members Intent**
- ✅ **Presence Intent** (optional)

### Bot Permissions
- `Manage Roles` — untuk auto rank sync
- `Send Messages` & `Embed Links` — komunikasi
- `Attach Files` — kirim kartu & PDF
- `Manage Messages` — bersihkan chat (opsional)
- `Read Message History` — untuk command

---

## 📁 Project Structure

```
raffbot-priv/
├── bot.py                  # Main entry point
├── .env                    # Environment config (token)
├── .gitignore
├── requirements.txt
├── start-bot.bat           # Windows quick launcher
├── start-bot.ps1           # PowerShell launcher
├── assets/
│   └── welcome_ref.png     # Welcome card template
├── src/
│   ├── __init__.py
│   ├── storage.py          # Journal data management
│   ├── ranks.py            # Hunter rank system
│   ├── image_generator.py  # Card & image generation
│   ├── pdf_ops.py          # PDF manipulation tools
│   ├── converter.py        # Document format converter
│   ├── pdf_export.py       # Journal PDF export
│   ├── gemini_client.py    # Gemini AI integration
│   ├── scheduler.py        # Reminder scheduler
│   ├── welcome_config.py   # Welcome/goodbye config
│   └── chat_xp.py          # Chat XP system
└── temp/                   # Temporary files
```

---

## 🔧 Dependencies

| Package | Version | Purpose |
|---|---|---|
| discord.py | ≥2.4.0 | Discord API |
| python-dotenv | ≥1.0.1 | Environment config |
| apscheduler | ≥3.10.0 | Reminder scheduler |
| fpdf2 | ≥2.8.0 | PDF generation |
| PyMuPDF | ≥1.25.3 | PDF manipulation |
| pypdf | ≥5.2.0 | PDF processing |
| Pillow | ≥11.1.0 | Image generation |
| img2pdf | ≥0.5.1 | Image to PDF |
| pdf2image | ≥1.17.0 | PDF to image |
| python-pptx | ≥1.0.2 | PPTX conversion |
| openpyxl | ≥3.1.5 | XLSX conversion |
| python-docx | ≥1.1.2 | DOCX conversion |
| pytesseract | ≥0.3.13 | OCR (optional) |
| aiofiles | ≥24.1.0 | Async file IO |
| httpx | ≥0.28.1 | HTTP client |

---

## 📜 License

This project is licensed under the MIT License.

---

<div align="center">
  <p>Built with ❤️ by <a href="https://github.com/Pidzzzz">Pidzzzz</a></p>
  <p>
    <a href="https://github.com/Pidzzzz/raffbot-discord">📦 Repository</a>
  </p>
  <br>
</div>
