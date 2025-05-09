# Advertising Dashboard MVP 🚀

Minimal prototype to satisfy the AlemX test-task requirements in **≤ 4 h**.

---

## ✨ What you can do

| Feature | Details |
|---------|---------|
| **Mock login** | Hard-coded demo user (`demo@alemx.com` / `demo123`) with JWT issued by FastAPI. |
| **Upload or link an image** | Drag-and-drop or paste a URL. |
| **Three campaign modes** | 1️⃣ *AI-Generate* (no image)<br>2️⃣ *Edit w/ reference* (DALL·E edit)<br>3️⃣ *Describe-then-generate* (GPT-4o Vision → DALL·E generate). |
| **Audience targeting** | Dual-range age slider (3–100), location text box, multi-select interests (add your own via a “+” chip). |
| **Submit a campaign** | Persists in-memory; logs payload in console. |
| **Campaign list** | Name, date, mock status, fake impressions/CTR, ad-copy headline, generated banner preview, modal enlarge. |

---

## 🛠 Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | **React + Vite** – plain CSS, no Tailwind. |
| Backend | **FastAPI (Python)** with OpenAI SDK. |
| Auth | Simple JWT encode/decode (no DB). |
| AI APIs | GPT-4o-mini (headline & vision), DALL·E 3 (`gpt-image-1`) for banners. |

---

## ⚡️ AI Super-powers

- **Code generation**: 80 % of boilerplate was scaffolded with ChatGPT-4o (prompts in `/prompts_history`).
- **Image wizardry**:  
  - *Edit mode* → passes the uploaded banner to DALL·E for remixing.  
  - *Inspiration mode* → GPT-4o Vision summarizes the image; the description is appended to the text prompt, then DALL·E generates a fresh banner.
- **Instant ad copy**: GPT-4o writes a concise headline (≤ 25 tokens).
- **Simulated analytics**: Impressions and clicks are randomised; CTR is computed.

⏱ **Time saved with AI:** ~60 % (scaffolding, regex validators, CSS snippets, mock data).

---

## 🚀 Local Setup

```bash
git clone https://github.com/<your-user>/alemx-ad-dashboard.git
cd alemx-ad-dashboard

# backend
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
export OPENAI_API_KEY=<your-key>
uvicorn backend.main:app --reload             # http://127.0.0.1:8000

# frontend (in a new terminal)
cd frontend
npm i
npm run dev                                   # http://127.0.0.1:5173
