# AIOS — Migration Context & Handoff Document

> Dokumen ini berisi ringkasan lengkap apa yang sudah dikerjakan, status saat ini, dan rencana ke depan untuk proyek **AIOS (Artificial Intelligence Operating System)** milik Aditiya. Ditulis untuk di-paste ke chat/AI lain sebagai instruksi konteks penuh, supaya tidak perlu mengulang dari awal.

---

## 1. Tentang Pemilik Proyek

- **Nama:** Aditiya
- **Role:** Full Stack AI & ML Developer | MTCNA Network Engineer | Agentic AI & Multi-RAG Systems, MLOps, Network Infrastructure, Full-Stack Systems
- Bekerja di **Vizartlabs** sebagai Full Stack AI Developer dan UI/UX & Brand Identity Designer
- Sebelumnya Network Technician di **PT Tunas Link Indonesia** (FTTH, fusion splicing)
- Mahasiswa Instrumentasi dan Automasi, Institut Teknologi Sumatera (ITERA); alumni SMKN 1 Bandar Lampung
- Memimpin tim di **GEMASTIK 2026** (Edge Computing & TinyML, IoT, SCADA/HMI) dan **LIDM 2026**; ikut **PKM-KC**
- Skill luas: full-stack dev (React/Svelte/Vue, Node/Go/FastAPI), AI/ML (PyTorch, LangChain, RAG), UI/UX & brand design, networking (MTCNA), Docker/DevOps, Google Cloud & Azure Generative AI, SCADA/PLC

**Cara komunikasi yang disukai:** teknis, langsung ke inti, tidak perlu jelaskan dasar-dasar yang sudah dikuasai. Jujur soal ketidakpastian API/versi/kompatibilitas — verifikasi lebih dihargai daripada asumsi (pernah kena masalah karena asumsi model tersedia sebagai hosted API, ternyata perlu self-host).

---

## 2. Konsep Besar: AIOS

AIOS adalah **organisasi eksekutif AI** — bukan satu asisten umum, tapi 5 "executive department" AI dengan tanggung jawab, wewenang, dan batasan yang jelas, terinspirasi struktur perusahaan teknologi modern. Dokumen resmi organisasinya (`ORGANIZATION.pdf`, sudah diupload dan dibaca penuh) mendefinisikan:

### Struktur Eksekutif

| Executive | Title | Domain | Framework (Aktual) |
|---|---|---|---|
| **Lyra Everlight** | Chief Strategy Officer (CSO) | Strategi bisnis, riset teknologi, market/competitive intelligence | **Hermes Agent** ✅ jalan |
| **Lyssa Ashbourne** | Chief Operations Officer (COO) | Automation, browser control, integrasi, eksekusi operasional | **OpenClaw** ✅ jalan |
| **Lysandra Moonveil** | Chief Creative Officer (CCO) | UI/UX, branding, design system, creative direction | **CrewAI** ⏸️ belum fix/ditunda |
| **Lucienne Nightfall** | Chief Engineering Officer (CENGO) | Software engineering, arsitektur, AI implementation, infra, security | **OpenHands** 🔧 sedang disetup |
| **Lunaria Valencrest** | Chief Knowledge & Data Intelligence Officer (CKDIO) | Knowledge management, RAG, memory, analytics | **LangGraph** ⏳ belum digarap |

> Catatan: dokumen `ORGANIZATION.pdf` resminya menulis "Primary Framework: Hermes" untuk semua executive — itu draf konseptual awal. Mapping framework aktual di atas adalah keputusan pragmatis Aditiya yang lebih baru dan yang sedang diimplementasikan.

### Prinsip Kunci dari Dokumen Organisasi
- **Single Owner Principle** — setiap tanggung jawab punya satu pemilik eksekutif, tidak ada ownership ganda
- **Specialization over Generalization** — tiap agent fokus mendalam di satu domain
- **Collaboration by Design** — executive saling melengkapi, bukan menggantikan
- Semua agent **wajib bisa diakses/dikontrol lewat Telegram chat**

---

## 3. Infrastruktur Bersama (semua agent)

- **9Router** — gateway lokal OpenAI-compatible di `http://localhost:20128/v1` (native di Windows, BUKAN Docker)
- Semua agent yang jalan di **container Docker** harus akses 9Router lewat `http://host.docker.internal:20128/v1` (bukan `localhost`, karena container punya network namespace terpisah dari host)
- **Docker Desktop** di Windows, dengan `.wslconfig` dibatasi: `memory=3GB, processors=4, swap=2GB, localhostForwarding=true`
- Struktur folder: tiap agent punya folder terpisah di `E:\DevOps-project\<Nama-Agent>`

---

## 4. Status Detail per Agent

### 🟣 Lyra Everlight — Hermes Agent (✅ SELESAI & JALAN)

- Folder: `E:\DevOps-project\Hermes-agent`
- Docker image custom: `hermes-agent-custom` (base: `nousresearch/hermes-agent:latest`)
- Model: combo **`Mavent-bot`** via 9Router (prioritas kecepatan + tool-calling): `nvidia/stepfun-ai/step-3.7-flash`, `groq/openai/gpt-oss-120b`, `mavent/DeepSeek-V4-Flash`, dll
- **STT:** NVIDIA Nemotron 3 Nano Omni (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`) via custom endpoint di 9Router — berhasil setelah beberapa percobaan 404 (model ini TIDAK tersedia sebagai hosted serverless endpoint standar NVIDIA, harus ditambahkan manual sebagai custom OpenAI-compatible provider)
- **TTS:** Microsoft Edge TTS (gratis)
- **Web search:** DuckDuckGo (`ddgs`) — perlu install manual via Dockerfile custom karena image dasar tidak menyertakannya (`uv pip install --python /opt/hermes/.venv/bin/python3 ddgs ...`, image ini pakai `uv`, BUKAN `pip` biasa)
- Dependency tambahan yang sudah di-install di image custom: `python-docx`, `openpyxl`, `pypdf`, `pdfplumber`, `Pillow`, `pytesseract` + `tesseract-ocr`, `beautifulsoup4`, `lxml`, `markdown`, `python-pptx`, `pandas`, `requests`
- **Akses file:** drive `D:\` dan `E:\` di-mount ke container (`/opt/access/D`, `/opt/access/E`) — drive `C:\` sengaja TIDAK di-mount untuk batasi risiko
- Bot Telegram terhubung, dikunci by user ID (private, hanya Aditiya)
- **SOUL.md** custom sudah dibuat berisi identitas Lyra + profil Aditiya + status setup
- Repo GitHub publik: **https://github.com/vizartid/Mavent-claw** (nama repo ini sebenarnya dipakai bersama untuk dokumentasi OpenClaw — cek konteks bagian 4b)
- Command jalanin gateway 24 jam:
  ```powershell
  docker run -d --name hermes --restart unless-stopped -v E:\DevOps-project\Hermes-agent:/opt/data -p 8642:8642 hermes-agent-custom gateway run
  ```

### 🟠 Lyssa Ashbourne — OpenClaw (✅ SELESAI & JALAN)

- Folder: `E:\DevOps-project\OpenClaw-agent`
- Image resmi: `ghcr.io/openclaw/openclaw:latest` (atau tag `:main` jika `latest` bermasalah — pernah ketemu bug "Setup cancelled" di security disclaimer step)
- Model: combo **`Mavent-claw`** via 9Router, disusun (kredit diabaikan sebagai faktor prioritas):
  ```
  Primary:   Qwen3.5-397B-A17B (unlimited)
  Fallback1: DeepSeek v4 Flash
  Fallback2: Minimax M3 (6 key rotasi)
  Fallback3: nvidia/stepfun-ai/step-3.7-flash
  ```
- **imageModel (vision):** Nemotron 3 Nano Omni
- **Embedding:** `nemotron-3-embed-1b` (via 9Router, provider adapter type `openai`)
- Gateway port: **18789**, bind address **Loopback (127.0.0.1)**, access protection **Token**
- **Memory LanceDB** aktif dengan Auto-Capture + Auto-Recall = Yes
- **OpenShell Sandbox** mode **mirror** (workspace lokal jadi basis sandbox) — field CLI OpenShell/gateway/policy dikosongkan (belum ada NVIDIA OpenShell CLI ter-install)
- **Search provider:** DuckDuckGo (experimental) — Brave Search jadi alternatif kalau nanti mau upgrade (butuh API key)
- **Google Meet plugin** aktif: transport `chrome`, Launch Chrome = Yes, Auto Join Guest Screen = **No** (tetap butuh approval manual), Delegate to Voice Call = No
- **Voice Call plugin** aktif tapi provider **mock** (dev/testing, bukan Twilio/Telnyx sungguhan) — Inbound Policy: **disabled**
- Plugin lain yang di-skip: GitHub Copilot provider, xAI plugin, Google Places API key, OpenAI Whisper API key (semua karena belum ada kredensial)
- Repo GitHub publik: **https://github.com/vizartid/Mavent-claw** — sudah lengkap dengan README (Shields badges, Skill Icons, Devicon, Mermaid diagram), `Dockerfile`, `docker-compose.yml`, `.env.example`, `.gitignore`, `SOUL.md` (versi template kosong untuk publik), `LICENSE` (MIT), `CHANGELOG.md`, `CONTRIBUTING.md`
- Command jalanin gateway:
  ```powershell
  docker run -d --name openclaw --restart unless-stopped -v E:\DevOps-project\OpenClaw-agent:/home/node/.openclaw -p 18789:18789 ghcr.io/openclaw/openclaw:latest openclaw gateway
  ```

### 🎨 Lysandra Moonveil — CrewAI (⏸️ DITUNDA)

- Sempat direncanakan pakai **LangGraph** (bukan CrewAI) di awal — sudah dibuat fondasi Tahap 1: `graph.py` (satu node chat sederhana via 9Router), `main.py` (entry point test lokal), `Dockerfile`, `requirements.txt`, `.env.example` di folder rencana `E:\DevOps-project\Lysandra-agent`
- **PERUBAHAN TERBARU (dari ORGANIZATION.pdf):** frameworknya diputuskan **CrewAI**, bukan LangGraph — tapi status "belum fix", jadi kemungkinan besar keputusan ini masih bisa berubah
- **Belum lanjut dikerjakan** — file LangGraph Tahap 1 sudah ada tapi mungkin tidak relevan lagi kalau jadi pindah ke CrewAI
- **Next step kalau dilanjutkan:** klarifikasi ulang framework final (CrewAI vs LangGraph), lalu bangun sesuai keputusan itu — termasuk bridge Telegram custom karena baik CrewAI maupun LangGraph sama-sama tidak punya integrasi Telegram bawaan

### 🔧 Lucienne Nightfall — OpenHands (🔧 SEDANG DIKERJAKAN)

- Folder rencana: `E:\DevOps-project\Lucienne-agent`
- **OpenHands tidak punya integrasi Telegram resmi** (masih GitHub Issue #13113, proposal terbuka) — dibangun **bridge custom**
- Model: combo **`Lucienne-cengo`** di 9Router:
  ```
  Primary:   Kimi 2.6
  Fallback1: Minimax M3 (belum fix)
  Fallback2: Qwen3.5-397B-A17B
  Fallback3: DeepSeek v4 Flash
  ```
- **Package pip resmi (terverifikasi):** `openhands-sdk` + `openhands-tools` (BUKAN `openhands-ai`, itu API lama/V0 yang sudah deprecated April 2026) — install keduanya dalam **satu command pip** (`pip install -U openhands-sdk openhands-tools`) supaya versinya saling cocok, jangan lewat `requirements.txt` biasa
- **Requirement Python ≥3.12** untuk `openhands-sdk`
- API resmi (V1 SDK, namespace `openhands.sdk`):
  ```python
  from openhands.sdk import LLM, Agent, Conversation, Tool
  from openhands.tools.file_editor import FileEditorTool
  from openhands.tools.task_tracker import TaskTrackerTool
  from openhands.tools.terminal import TerminalTool
  ```
- File yang sudah dibuat: `docker-compose.yml` (2 service: `openhands-runtime` + `lucienne-bridge`), `Dockerfile`, `requirements.txt`, `telegram_bridge.py` (bridge dengan lapisan konfirmasi untuk aksi berisiko — shell exec, delete, git push, dll HARUS approve dulu di Telegram, karena headless mode OpenHands defaultnya auto-approve semua), `openhands_runner.py` (wrapper SDK, pakai pola callback per-event untuk streaming ke Telegram, BUKAN blocking `conversation.run()` biasa), `.env.example`, `.gitignore`, `.openhands/microagents/lucienne-identity.md` (skill/identitas Lucienne via mekanisme **Microagents** bawaan OpenHands)
- **BELUM DIVERIFIKASI (perlu dicek user sebelum production):**
  1. Nama parameter constructor `Conversation(..., callback=...)` — perlu run `help(Conversation)` di container untuk pastikan
  2. Bentuk persis object `event` yang diterima callback
  3. Apakah ada API pause/resume sungguhan untuk intercept aksi berisiko SEBELUM dieksekusi (bukan cuma dilaporkan sesudahnya) — ini gap keamanan yang sudah diberi catatan eksplisit di kode, JANGAN dianggap sudah aman sampai diverifikasi
- **Masalah build terakhir:** dependency resolution lambat karena constraint versi longgar (`>=1.19.1`) bikin pip mundur cek banyak versi `lmnr` (dependency internal). **Sudah diperbaiki**: requirements.txt tanpa pin versi + install `openhands-sdk`/`openhands-tools` di command pip terpisah dari requirements.txt lainnya
- **Next step:** build ulang dengan Dockerfile yang sudah diperbaiki, lalu jalankan `docker exec -it lucienne-bridge python -c "from openhands.sdk import Conversation; help(Conversation)"` untuk verifikasi API sebelum dipakai serius

### 📚 Lunaria Valencrest — LangGraph (⏳ BELUM DIGARAP SAMA SEKALI)

- Belum ada file/folder dibuat
- Domain: Knowledge management, RAG, organizational memory, analytics
- Kemungkinan bisa reuse sebagian pola dari Tahap 1 Lysandra yang sudah dibuat (LangGraph node sederhana + 9Router binding), karena frameworknya sama

---

## 5. Keputusan & Pelajaran Penting (jangan diulang salah)

1. **`host.docker.internal` vs `localhost`** — SELALU pakai `host.docker.internal` untuk container yang perlu akses 9Router (native Windows), bukan `localhost`. Ini kesalahan paling sering terjadi di awal setup tiap agent.
2. **Hermes pakai `uv`, bukan `pip`** — kalau bikin Dockerfile custom untuk image berbasis Hermes, gunakan `uv pip install --python /opt/hermes/.venv/bin/python3 ...`
3. **File `Dockerfile` di Windows sering ke-save sebagai `Dockerfile.txt`** oleh Notepad — selalu cek dengan `Get-ChildItem` sebelum `docker build`
4. **Wizard TUI (OpenClaw, dll) biasanya TIDAK punya tombol "back"** — ESC seringkali membatalkan seluruh proses, bukan mundur satu langkah. Kalau ragu di suatu field, lebih aman kosongkan (Enter) daripada menebak dan harus ulang dari awal
5. **Model "Free Endpoint" di katalog NVIDIA build ≠ hosted serverless API otomatis** — badge itu bisa berarti cuma tersedia untuk dicoba di playground browser, bukan API produksi siap pakai. SELALU test dulu dengan curl manual sebelum asumsi endpoint tersedia
6. **Constraint versi pip yang longgar (`>=x.x.x`) bisa bikin dependency resolution sangat lambat** kalau ada banyak versi historis — lebih baik unpinned total (biar pip ambil versi terbaru langsung) atau pin eksak, hindari lower-bound longgar untuk package yang sering update
7. **Jangan mount drive `C:\`** ke container manapun — cukup `D:\` dan `E:\` untuk membatasi blast radius kalau ada insiden keamanan
8. **Headless mode OpenHands auto-approve semua aksi secara default** — ini BAHAYA kalau di-bridge ke Telegram tanpa modifikasi. Bridge custom WAJIB menambahkan lapisan konfirmasi sendiri, jangan pernah expose headless mode polos ke Telegram
9. **Ketiga bot Telegram semuanya pakai token berbeda** (jangan reuse token yang sama antar agent) dan masing-masing dikunci ke Telegram User ID Aditiya saja (private, bukan grup publik)

---

## 6. Rencana ke Depan (belum dikerjakan)

- [ ] Finalisasi framework Lysandra (CCO): CrewAI vs LangGraph — perlu keputusan final dulu
- [ ] Selesaikan setup Lucienne (CENGO): verifikasi API OpenHands SDK yang benar via `help()`, lengkapi bridge Telegram dengan pause/resume aksi berisiko yang sungguhan (bukan cuma post-hoc report)
- [ ] Mulai dari nol: Lunaria (CKDIO) — LangGraph untuk knowledge/RAG/memory
- [ ] Setelah kelima executive jalan: pikirkan mekanisme **koordinasi lintas-agent** (misal: bagaimana Lyra bisa "memberi tahu" Lysandra soal strategi produk, sesuai Executive Collaboration Framework di `ORGANIZATION.pdf`) — ini belum ada implementasi teknisnya sama sekali, baru konsep di dokumen
- [ ] Pertimbangkan ulang keamanan kalau nanti agent-agent ini dibuka untuk lebih dari satu user (saat ini semua personal-only by design)

---

## 7. File Referensi yang Sudah Dibuat

| Agent | File-file utama |
|---|---|
| Hermes (Lyra) | `Dockerfile`, `docker-compose.yml`, `.gitignore`, `.env.example`, `SOUL.md`, `README.md`, `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md` — repo publik di github.com/vizartid |
| OpenClaw (Lyssa) | Sama seperti di atas, repo: **github.com/vizartid/Mavent-claw** |
| Lysandra (LangGraph, ditunda) | `app/graph.py`, `app/main.py`, `Dockerfile`, `requirements.txt`, `.env.example`, `.gitignore` |
| Lucienne (OpenHands) | `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `telegram_bridge.py`, `openhands_runner.py`, `.env.example`, `.gitignore`, `.openhands/microagents/lucienne-identity.md` |

---

## Instruksi untuk AI yang Melanjutkan

Jika kamu adalah AI yang menerima dokumen ini di chat baru: baca seluruh konteks di atas sebagai state proyek AIOS saat ini. Jangan mengulang pertanyaan dasar yang jawabannya sudah tercantum di sini (misal "9Router itu apa", "kenapa pakai host.docker.internal"). Lanjutkan dari titik "Rencana ke Depan" di atas, dan ikuti seluruh "Keputusan & Pelajaran Penting" agar tidak mengulang kesalahan yang sudah pernah terjadi. Selalu verifikasi API/versi package sebelum menulis kode final — jangan menebak nama fungsi/parameter SDK yang belum dikonfirmasi, seperti prinsip yang sudah dipegang sepanjang proyek ini.
