# Blood Warriors AI - Intelligent Thalassemia Care Copilot

Blood Warriors AI is an autonomous care coordination and predictive analytics platform built to support Thalassemia patients. The platform optimizes donor rotations, prevents coordinator burnout, and automates emergency outreach using stateful AI pipelines and machine learning.

---

## 🌟 Key Features

### 1. LangGraph Transfusion Orchestrator
- A stateful, asynchronous state machine that manages the transfusion lifecycle:
  - **Request Creation** ➡️ **Donor Matching** ➡️ **Outreach Dispatch** ➡️ **Response Processing** ➡️ **Appointment Scheduling**
  - Pauses execution while awaiting donor confirmations and resumes automatically when replies are received.
  - Implements **Zero-Donor Fallbacks**: If no pool/emergency donors are available, the machine dispatches an alert message to the regional coordinator.

### 2. Predictive AI Engines
- **Donor Availability (XGBoost):** Predicts active donor availability based on days since last donation, historical donation count, and engagement score.
- **Donor Churn Risk (Random Forest):** Evaluates donor drop-off probability using log response rates and engagement score.
- **Dynamic Date-Aware Matching:** Evaluates donor eligibility (the 90-day periodic lockout) relative to the **patient's expected next transfusion date** rather than today's date, ensuring optimal future matching and rotation.

### 3. Live Two-Way Communication
- **Interactive WhatsApp Webhook:** Connects with Twilio to receive WhatsApp replies ("Accept" or "Decline") directly from donors, updating state registers and advancing the workflow in real-time.
- **AWS SNS SMS Integration:** Automatically dispatches instant thank-you SMS alerts to donors upon donation completion.

### 4. Administrator Coordination Dashboard
- Real-time workflow tracker containing interactive step progress indicators.
- **Admin Control Panel:** Allows coordinators to "Record Successful Donation" only when the donor has successfully given blood.
- Deferring the 90-day rest period block to completion prevents errors from cancelled appointments or no-shows.
- **HPLC Prevention Panel:** Tracks Village, School, and Corporate thalassemia screening drives to help identify carrier risks.

---

## 🛠️ Technology Stack

- **Backend:**
  - FastAPI (Python)
  - LangGraph (State Machine Orchestration)
  - XGBoost & RandomForest (ML Modeling & Classification)
  - SQLAlchemy & SQLite (Database Layer)
  - Twilio API (Two-Way WhatsApp/SMS)
  - Boto3 AWS SDK (One-Way SMS via AWS SNS)
- **Frontend:**
  - Next.js & React (TypeScript)
  - Zustand (State Management)
  - Tailwind CSS (Styling)

---

## 🚀 Getting Started

### 1. Configuration (`.env`)
Copy the template file to configure your local keys:
```bash
cp .env.example .env
```
Fill in the values in your `.env` file:
- `TWILIO_ACCOUNT_SID` & `TWILIO_AUTH_TOKEN` (for outreach)
- `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY` (for AWS SNS alerts)
- `ADMIN_PHONE_NUMBER` (your mobile number to test the demo outreach)
- `USE_LOCAL_MOCKS=FALSE` (set to `FALSE` to send live messages; `TRUE` to run offline mocks)

### 2. Run with Docker Compose (Recommended)
Launch all services (PostgreSQL, Redis, Backend, Frontend) with a single command:
```bash
docker compose up -d --build
```
Access the application:
- Frontend: `http://localhost:3000`
- Backend API Docs: `http://localhost:8000/docs`

### 3. Running Locally

#### Backend:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

#### Frontend:
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing & Verification

A comprehensive test suite is included to verify predictive engines, database populating, consent-aware exclusions, and transfusion LangGraph workflow transitions:

```bash
python verify.py
```
