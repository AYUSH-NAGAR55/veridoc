# VeriDoc

Turns messy PDFs into verified, searchable knowledge — and lets you ask questions about them with source-backed answers.

Upload a PDF → VeriDoc figures out what each page actually is (text, scanned, table) → extracts and structures the important fields → **validates them against each other** (does the math check out? are dates real?) → routes anything uncertain to a human review queue → and only then makes the document searchable through a grounded Q&A chat.

## Running it locally without Docker (Windows)

You need two things installed first: **Python** and **Node.js**. Then you run the backend and frontend as two separate terminal windows.

### 1. Install prerequisites (one-time)

- **Python**: download from [python.org/downloads](https://python.org/downloads) — during install, tick **"Add Python to PATH"** before clicking Install.
- **Node.js**: download the LTS version from [nodejs.org](https://nodejs.org) — just click through the installer defaults.
- **Tesseract OCR** (optional, only needed for scanned/image-based PDFs): download the Windows installer from [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki), install with defaults. If you skip this, everything still works — scanned pages just won't have text extracted until you install it later.

Close and reopen any terminal windows after installing these, so the new PATH entries take effect.

### 2. Start the backend

Open a terminal (Command Prompt or PowerShell) in the `veridoc\backend` folder:

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Leave this terminal running. You should see `Uvicorn running on http://0.0.0.0:8000`.

### 3. Start the frontend

Open a **second, separate** terminal in the `veridoc\frontend` folder:

```bash
cd frontend
npm install
npm run dev
```

Leave this running too. It'll print a local URL — usually `http://localhost:5173`.

### 4. Open the app

Go to **http://localhost:5173** in your browser.

### To stop it
Press `Ctrl + C` in each terminal window.

### To run it again later
You don't need to reinstall anything — just repeat steps 2 and 3 (skip the `pip install`/`npm install` lines, just run the `venv\Scripts\activate` then `uvicorn ...` command, and `npm run dev` in the other window).

---

## Deploying it for free (no Docker knowledge needed)

The easiest free option is **Hugging Face Spaces** — it builds and hosts the app from the files in this folder, no Docker install and no credit card required.

1. Go to [huggingface.co](https://huggingface.co), make a free account.
2. Click **New Space** (top right → your profile → New Space).
3. Give it a name, pick any license, and under **Space SDK** choose **Docker**. Pick the free **CPU basic** hardware tier.
4. Once it's created, upload every file in this project folder into the Space (there's an "Files" tab with an upload button — or use `git` if you're comfortable with it). Make sure the root-level `Dockerfile` (not the ones inside `backend/` or `frontend/`) ends up at the top level of the Space.
5. Hugging Face automatically builds and starts it. First build takes a few minutes — you'll see live logs. When it's done, you get a public URL like `https://huggingface.co/spaces/yourname/veridoc`.

That's it — no local Docker, no command line required.

**Worth knowing:** the free tier sleeps after inactivity (next visit takes ~30-60 seconds to wake up), and uploaded PDFs/the database reset if the Space restarts. Fine for showing this off; not meant for storing real documents long-term.

## Running it locally

**Docker (recommended):**
```bash
docker compose up --build
```
Then open **http://localhost:5173**. The frontend proxies API calls to the backend automatically.

**Without Docker:**
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```
Requires `tesseract-ocr` installed locally for the OCR step (`apt install tesseract-ocr` on Ubuntu/Debian, `brew install tesseract` on macOS).

## What's implemented

Every step from the spec runs against real files, not mocked data:

| Step | How |
|---|---|
| Understand the PDF | PyMuPDF + pdfplumber inspect every page and classify it as text / scanned / table / mixed |
| Extract content | PyMuPDF for text, pdfplumber for tables (kept as structured rows, not flattened), OpenCV-cleaned + Tesseract OCR for scanned pages |
| Extract structured fields | Pattern-anchored extraction for invoices (Vendor, Invoice Number, Subtotal, Tax, Total…) and financial reports (Revenue, Expenses, Net income…) |
| Validate | Real arithmetic cross-checks (Subtotal + Tax = Total, Revenue − Opex ≈ Net income), date/number sanity checks |
| Confidence & review queue | Every field gets a score; ≥90% auto-accepts, anything lower lands in the **Review** tab with Accept / Correct |
| Knowledge base + Q&A | Verified page content is chunked and indexed; the chat tab retrieves the right chunk or structured field and answers with a page citation and confidence |

## Where this build diverges from the spec's tech stack, and why

This was built in a sandboxed environment with **no GPU and no access to model-hosting services**, so two substitutions were made — both isolated behind small, swappable interfaces so upgrading later doesn't touch the rest of the pipeline:

- **LLM (Ollama) → rule-based extraction.** `pipeline/structurer.py` uses field-anchored regex instead of an LLM call. It's honest about its limits: it works well for the invoice/financial-report shapes in the spec, but won't generalize to arbitrary document types the way an LLM would. Swapping in Ollama means replacing the body of `extract_fields()` with a structured-output call — the validator, confidence scoring, and review queue downstream don't need to change.
- **Sentence Transformers + FAISS → TF-IDF (scikit-learn).** `pipeline/indexer.py`'s `VectorIndex` class exposes just `fit()` and `search()`, the same shape a FAISS-backed version would need, so it's a drop-in swap once embedding models are available.

Everything else — PyMuPDF, pdfplumber, PaddleOCR's role (via Tesseract, since PaddleOCR's model downloads weren't reachable here), OpenCV, Pydantic-style validation, and PostgreSQL's role (via SQLite for a zero-setup demo, same schema shape) — runs as real, working code rather than a mock.

## Project structure

```
veridoc/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── pipeline/          # Steps 2-10 of the spec
│   │   └── routers/           # documents / review / chat endpoints
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/        # ConfidenceRing, ReviewItem, DocumentChat, etc.
│   │   ├── pages/              # DocumentsPage, DocumentDetailPage
│   │   └── lib/api.js
│   └── Dockerfile
└── docker-compose.yml
```
