# Blood Warriors AI - System Architecture

Blood Warriors AI is a production-grade full-stack platform coordinating Thalassemia patient transfusions, blood donor availability predictions, and carrier screening awareness.

---

## 1. System Components

### Frontend (Next.js 15)
- **Framework**: Next.js 15 App Router with TypeScript.
- **Styling**: Tailwind CSS utilizing curated rose/crimson dark-mode tokens.
- **State Management**: Zustand lightweight global stores.
- **Charting**: Recharts responsive client-side forecasting graphs.

### Backend (FastAPI)
- **REST framework**: FastAPI with automated Swagger documentation.
- **ORM**: SQLAlchemy using async PG/SQLite connection pools.
- **Task Runner**: Built-in async triggers for ML pipelines and state transitions.

### AI Layer
- **Donor Availability**: XGBoost regressor predicting real-time donor readiness.
- **Donor Churn Risk**: RandomForest regressor modeling donor attrition probabilities.
- **Transfusion Orchestrator**: LangGraph compiled state machine implementing recursive matching and outreach retry queues.
- **Awareness Chatbot**: TF-IDF and Cosine Similarity-based vector store matching contexts for AWS Bedrock Claude queries.

---

## 2. Database Design

```mermaid
erDiagram
    donors {
        string id PK
        string name
        string phone
        string email
        string blood_group
        string city
        float latitude
        float longitude
        int age
        string gender
        string donor_type
        int donations_till_date
        string last_donation_date
        string next_eligible_date
        float engagement_score
        float availability_score
        float churn_risk
        string active_status
    }
    patients {
        string id PK
        string name
        string blood_group
        string city
        float quantity_required
        string last_transfusion_date
        string expected_next_transfusion_date
        string risk_level
    }
    donor_patient_matches {
        int id PK
        string patient_id FK
        string donor_id FK
        float match_score
        string relationship_type
    }
    donation_history {
        int id PK
        string donor_id FK
        string patient_id FK
        string donation_date
        string status
        string notes
    }
    outreach_logs {
        int id PK
        string donor_id FK
        string message
        string response
        string response_status
    }

    patients ||--o{ donor_patient_matches : matches
    donors ||--o{ donor_patient_matches : matches
    donors ||--o{ donation_history : donates
    patients ||--o{ donation_history : receives
    donors ||--o{ outreach_logs : logs
```

---

## 3. AI Smart Matching Engine

Matches are computed and ranked based on a weighted 40-20-20-10-10 composite formula:

$$Score = (Compatibility \times 0.40) + (Eligibility \times 0.20) + (Availability \times 0.20) + (Engagement \times 0.10) + (Distance \times 0.10)$$

1. **Compatibility (40%)**: Strict ABO-Rh compatibility checks (incompatible donors filtered out).
2. **Eligibility (20%)**: Verification that current date is past the donor's `next_eligible_date` window.
3. **Availability (20%)**: Predicted probability from the XGBoost availability model.
4. **Engagement (10%)**: Normalized donor historical participation rating.
5. **Distance (10%)**: Haversine distance calculation mapped to a score between 0.0 (50km+) and 1.0 (0km).

---

## 4. LangGraph Transfusion Orchestration

The transfusion coordination cycle is automated via a state machine that handles pauses for donor actions:

```mermaid
graph TD
    A[Patient Request] --> B[Find Donors]
    B --> C[Rank Donors]
    C --> D[Generate Outreach]
    D -->|Pause & Wait for WhatsApp| E{Response?}
    E -->|Accepted| F[Schedule Donation]
    E -->|Declined / Timeout| G[Clear Donor & Re-try]
    G --> D
    F --> H[Completed]
    G -->|No More Donors| I[Failed & Escalate]
```

1. **Patient Request**: Validates request parameters and registers workflow.
2. **Find Donors**: Queries active compatible pool.
3. **Rank Donors**: Scores list using the Smart Matching composite scoring.
4. **Generate Outreach**: Selects top candidate and sends WhatsApp notification, pausing graph execution.
5. **Process Response**: Receives response. If accept, transitions to schedule. If decline, clears state and loops back to outreach next candidate.
6. **Schedule Donation**: Records appointment and updates donor eligibility calendars (+90 days).
