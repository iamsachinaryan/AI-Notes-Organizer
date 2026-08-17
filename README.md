# 🧠 AI Notes Organizer — Enterprise v3.0

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python"/>
  <img src="https://img.shields.io/badge/React-19-cyan?style=for-the-badge&logo=react"/>
  <img src="https://img.shields.io/badge/FastAPI-Backend-green?style=for-the-badge&logo=fastapi"/>
  <img src="https://img.shields.io/badge/AI-Gemini-purple?style=for-the-badge&logo=google"/>
  <img src="https://img.shields.io/badge/Platform-Windows-blue?style=for-the-badge&logo=windows"/>
  <img src="https://img.shields.io/badge/License-MIT-orange?style=for-the-badge"/>
</p>

<p align="center">
  <b>Stop searching for notes, start focusing on your studies.</b>
</p>

---

## 🧠 About the Project

AI Notes Organizer is an **AI-powered full-stack system** that automatically:

- 📂 Accepts PDF notes via drag & drop
- 🖋️ Extracts text using Google Vision OCR
- 🧠 Classifies subject using Gemini AI
- 📚 Organizes files into subject-wise folders
- 🔍 Provides a searchable notes library

**Stack:** React (Frontend) + FastAPI (Backend) + Google Gemini AI

---

## 💻 Installation Guide (New Laptop Setup)

### ✅ Step 1 — Install Prerequisites

Make sure these are installed on the new laptop:

| Tool | Download Link | Version |
|------|--------------|---------|
| Python | https://www.python.org/downloads/ | 3.9+ |
| Node.js | https://nodejs.org/ | 18+ |
| Git | https://git-scm.com/downloads | Latest |
| Poppler | https://github.com/oschwartz10612/poppler-windows/releases/ | Latest |

> ⚠️ **Poppler Setup (Important):**
> 1. Download the zip from the link above
> 2. Extract it anywhere (e.g., `C:\poppler`)
> 3. Add `C:\poppler\Library\bin` to Windows PATH
>    - Search "Environment Variables" → Edit Path → Add New → Paste path → OK

---

### ✅ Step 2 — Clone the Project

Open **Command Prompt** or **PowerShell** and run:

```bash
git clone https://github.com/iamsachinaryan/AI-Notes-Organizer.git
cd AI-Notes-Organizer
```

---

### ✅ Step 3 — Setup Backend (Python)

```bash
pip install -r requirements.txt
pip install fastapi uvicorn
```

---

### ✅ Step 4 — Setup Frontend (React)

```bash
cd frontend
npm install
cd ..
```

---

### ✅ Step 5 — Create `.env` File

In the project root folder, create a file named `.env` and paste:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

> 🔑 **Get Gemini API Key:**
> Go to https://aistudio.google.com/app/apikey → Create API Key → Copy & paste above

---

### ✅ Step 6 — Run the Project

You need **2 terminals** open at the same time:

**Terminal 1 — Backend:**
```bash
python -m uvicorn server:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm start
```

App will automatically open at **http://localhost:3000** 🚀

---

## 📁 Project Structure

```
AI-Notes-Organizer/
├── server.py           # FastAPI backend server
├── extractor.py        # Google Vision OCR engine
├── classifier.py       # Gemini AI subject classifier
├── registry.py         # SQLite notes database
├── brain.py            # Core AI logic
├── requirements.txt    # Python dependencies
├── .env                # API keys (create manually)
├── Organized_Notes/    # Auto-created notes folders
└── frontend/           # React web app
    ├── src/
    │   ├── App.js          # Main app
    │   ├── Upload.js       # Upload page
    │   └── ViewNotes.js    # Notes library
    └── package.json
```

---

## 🔐 Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Your Google Gemini API key |

---

## 📝 System Requirements

- Windows 10 / 11
- Python 3.9+
- Node.js 18+
- Internet connection (for Gemini AI)
- Poppler (for PDF processing)

---

## 👨‍💻 Developer

**Sachin Aryan**
🚀 Lead Developer & Visionary

---

## 📜 License

MIT License © 2026 Sachin Aryan
