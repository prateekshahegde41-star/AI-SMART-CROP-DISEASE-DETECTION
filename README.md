# VANYA — Smart Crop Disease Detection & Farmer Advisory System

> **PS 01: AI-Powered Smart Agriculture Disease Detection System**  
> Mobile-first precision farming platform: Multi-image lesion segmentation, confidence-weighted aggregation, temporal plant progression, environmental risk modeling, empirical yield estimation, and conversational agronomic advisory.

---

## 🏗️ Architecture Overview

- **Frontend (`app/`)**: Streamlit mobile-first web app with custom green theme, session persistence via cookies across mobile refreshes, role-based dynamic navigation (`st.navigation`), card-based history with filters, and interactive outbreak hotspot telemetry.
- **Backend (`api/`)**: FastAPI server providing multi-image inference aggregation, classical OpenCV GrabCut lesion segmentation (`severity.py`), Open-Meteo micro-climate disease risk evaluation (`risk.py`), plant tracking across visits, and empirical yield loss estimation (`yield_estimator.py`).
- **Database & Auth (Supabase)**: User authentication, role-based access control (RLS), profiles, plant tracking, predictions queue, and `avatars` media bucket.
- **Knowledge Base (`data/guidance.json`)**: Curated and verified management, causes, symptoms, prevention, treatment, and spread guidance cited from ICAR, State Agricultural Universities (TNAU, PAU, UAS), and agricultural extensions.

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites & Virtual Environment
```powershell
# Clone and enter repo
cd Agri-AI

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install core dependencies
pip install -r requirements.txt

# (Optional) Install PyTorch CPU build for live model inference
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### 2. Configuration & Secrets

#### Backend Secrets (`.env`)
Create `.env` in the repository root (do **never** commit `.env`):
```ini
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-supabase-publishable-key
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
```
*(If Supabase credentials are not configured, the backend automatically runs in offline/in-memory demo mode).*

#### Frontend Secrets (`.streamlit/secrets.toml`)
Create `.streamlit/secrets.toml` (or configure via Streamlit Cloud dashboard):
```toml
API_URL = "http://localhost:8000"
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "your-supabase-publishable-key"
```

---

## 🗄️ Supabase Setup Instructions

1. Open your [Supabase Project Dashboard](https://supabase.com/dashboard) and go to the **SQL Editor**.
2. Open [supabase_schema.sql](file:///c:/Agri-AI/supabase_schema.sql) and execute its contents. This will:
   - Create the `public.profiles` table with row-level security (RLS).
   - Set up the automatic `on_auth_user_created` trigger for profile initialization on signup.
   - Create the `public.plants` table for plant tracking across repeated farm visits.
   - Create `public.predictions` and `public.verifications` tables.
   - Create the `avatars` public storage bucket with upload and update policies.
3. **Promote an Account to Admin**:
   To elevate any registered account to expert administrator status, run in the Supabase SQL editor:
   ```sql
   update public.profiles
   set role = 'admin'
   where email = 'your-email@example.com';
   ```

---

## 🏃 Running the Application

### Start the FastAPI Backend (Terminal 1)
```powershell
uvicorn api.main:app --reload --port 8000
```
- Interactive API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

### Start the Streamlit Frontend (Terminal 2)
```powershell
streamlit run app/Home.py
```
- App UI opens at: [http://localhost:8501](http://localhost:8501)

---

## 🌟 Key Features & Improvements

### 1. Robust Multi-Image Aggregation & Clarity Flags
- Accepts up to 10 leaf photos or live camera captures.
- Blurry images are **never rejected**; instead, Laplacian variance calculates a `low_clarity` warning flag while still analyzing the leaf.
- Final disease prediction uses a **confidence-weighted vote** across all uploaded leaves.
- Final severity % is computed as the **mean of per-image severity percentages**.
- Segmented lesion masks (red overlay) and leaf contours (green contour) are rendered for every photograph.

### 2. Plant Tracking & Progression
- Assign a custom plant tag (e.g. `Tomato-Bed-1`) to track individual plants over time.
- Compares severity against previous checkups to alert if infection is **spreading**, **improving**, or **unchanged**.

### 3. Empirical Harvest Yield Estimation (`POST /estimate/yield`)
- Calculates estimated harvest loss % and remaining yield from:
  $$\text{Loss \%} = \min(90\%, \text{Base Severity Loss} \times \text{Pathogen Virulence Factor} \times \text{Weather Risk Factor})$$
- Default crop yield benchmarks per acre are provided with full transparency into formulas and assumptions.

### 4. Role-Based Admin & Dynamic Navigation (`st.navigation`)
- Regular farmers only see `[Detect, History, Crop Suitability, Outbreak Map]`.
- The `Admin Dashboard` is **strictly hidden** and only added if the user possesses the verified `role == 'admin'` in `profiles`.
- Backend endpoints under `/admin/*` validate Supabase bearer JWTs server-side and block unauthorized access with `HTTP 403 Forbidden`.
- Features an **Export Verified Corrections (CSV)** download for offline model fine-tuning.

### 5. Verified Agronomic Chatbot (`api/chatbot.py`)
- Floating round chatbot panel active only after disease detection.
- Fast word-boundary keyword and `rapidfuzz` intent recognition for: `about`, `causes`, `symptoms`, `prevention`, `treatment`, `spread`.
- Substring bug fixed (whole word matching prevents `"this"` from falsely triggering `"hi"`).
- Off-topic inquiries are politely declined without defaulting to generic management tips.
- Includes quick-reply chips and session history.
