const getBaseUrl = () => {
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    if (hostname !== "localhost" && hostname !== "127.0.0.1") {
      return `http://${hostname}:8000/api/v1`;
    }
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
};

const BASE_URL = getBaseUrl();


async function request(endpoint: string, options: RequestInit = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };
  try {
    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`API Request failed for ${endpoint}:`, error);
    throw error;
  }
}

export interface Donor {
  id: string;
  name: string;
  phone: string;
  email: string;
  blood_group: string;
  city: string;
  latitude?: number;
  longitude?: number;
  age: number;
  gender: string;
  donor_type: string;
  donations_till_date: number;
  last_donation_date?: string;
  next_eligible_date?: string;
  engagement_score: number;
  availability_score: number;
  churn_risk: number;
  active_status: string;
  created_at: string;
  updated_at: string;
}

export interface Patient {
  id: string;
  name: string;
  blood_group: string;
  city: string;
  quantity_required: number;
  last_transfusion_date?: string;
  expected_next_transfusion_date?: string;
  risk_level: string;
  created_at: string;
}

export const apiService = {
  // Patients
  async getPatients(): Promise<Patient[]> {
    try {
      return await request("/patients");
    } catch {
      return MOCK_PATIENTS;
    }
  },

  async getPatient(id: string): Promise<Patient> {
    try {
      return await request(`/patients/${id}`);
    } catch {
      return MOCK_PATIENTS.find(p => p.id === id) || MOCK_PATIENTS[0];
    }
  },

  async createPatient(patient: Partial<Patient>): Promise<Patient> {
    try {
      return await request("/patients", {
        method: "POST",
        body: JSON.stringify(patient),
      });
    } catch {
      const newPatient = {
        ...patient,
        id: `pat-${Math.floor(Math.random() * 9000 + 1000)}`,
        created_at: new Date().toISOString(),
      } as Patient;
      MOCK_PATIENTS.unshift(newPatient);
      return newPatient;
    }
  },

  async updatePatient(id: string, patient: Partial<Patient>): Promise<Patient> {
    try {
      return await request(`/patients/${id}`, {
        method: "PUT",
        body: JSON.stringify(patient),
      });
    } catch {
      const idx = MOCK_PATIENTS.findIndex(p => p.id === id);
      if (idx !== -1) {
        MOCK_PATIENTS[idx] = { ...MOCK_PATIENTS[idx], ...patient };
        return MOCK_PATIENTS[idx];
      }
      throw new Error("Patient not found");
    }
  },

  async deletePatient(id: string): Promise<any> {
    try {
      return await request(`/patients/${id}`, { method: "DELETE" });
    } catch {
      const idx = MOCK_PATIENTS.findIndex(p => p.id === id);
      if (idx !== -1) {
        MOCK_PATIENTS.splice(idx, 1);
      }
      return { status: "success" };
    }
  },

  // Donors
  async getDonors(): Promise<Donor[]> {
    try {
      return await request("/donors");
    } catch {
      return MOCK_DONORS;
    }
  },

  async getDonor(id: string): Promise<Donor> {
    try {
      return await request(`/donors/${id}`);
    } catch {
      return MOCK_DONORS.find(d => d.id === id) || MOCK_DONORS[0];
    }
  },

  async createDonor(donor: Partial<Donor>): Promise<Donor> {
    try {
      return await request("/donors", {
        method: "POST",
        body: JSON.stringify(donor),
      });
    } catch {
      const newDonor = {
        ...donor,
        id: `dnr-${Math.floor(Math.random() * 9000 + 1000)}`,
        donations_till_date: 0,
        availability_score: 0.75,
        churn_risk: 0.15,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      } as Donor;
      MOCK_DONORS.unshift(newDonor);
      return newDonor;
    }
  },

  async updateDonor(id: string, donor: Partial<Donor>): Promise<Donor> {
    try {
      return await request(`/donors/${id}`, {
        method: "PUT",
        body: JSON.stringify(donor),
      });
    } catch {
      const idx = MOCK_DONORS.findIndex(d => d.id === id);
      if (idx !== -1) {
        MOCK_DONORS[idx] = { ...MOCK_DONORS[idx], ...donor };
        return MOCK_DONORS[idx];
      }
      throw new Error("Donor not found");
    }
  },

  async deleteDonor(id: string): Promise<any> {
    try {
      return await request(`/donors/${id}`, { method: "DELETE" });
    } catch {
      const idx = MOCK_DONORS.findIndex(d => d.id === id);
      if (idx !== -1) {
        MOCK_DONORS.splice(idx, 1);
      }
      return { status: "success" };
    }
  },

  // AI Matches
  async getTopMatches(patientId: string): Promise<any> {
    try {
      return await request(`/ai/match/${patientId}`);
    } catch {
      // client mock matches
      const patient = MOCK_PATIENTS.find(p => p.id === patientId) || MOCK_PATIENTS[0];
      const compatible = MOCK_DONORS.filter(d => d.blood_group === patient.blood_group);
      const recs = compatible.map((d, index) => ({
        donor_id: d.id,
        name: d.name,
        blood_group: d.blood_group,
        match_score: Math.max(0.4, 0.98 - index * 0.05),
        distance_km: Math.round((2.4 + index * 4.1) * 10) / 10,
        availability_score: d.availability_score,
        engagement_score: d.engagement_score,
        eligibility: "eligible",
      }));
      return { patient_id: patientId, recommendations: recs };
    }
  },

  async getChurnScores(): Promise<any> {
    try {
      return await request("/ai/churn");
    } catch {
      const donors = MOCK_DONORS.map(d => ({
        donor_id: d.id,
        name: d.name,
        blood_group: d.blood_group,
        score: d.churn_risk,
      })).sort((a, b) => b.score - a.score);
      return { donors: donors.slice(0, 15) };
    }
  },

  async getAvailabilityScores(): Promise<any> {
    try {
      return await request("/ai/availability");
    } catch {
      const donors = MOCK_DONORS.map(d => ({
        donor_id: d.id,
        name: d.name,
        blood_group: d.blood_group,
        score: d.availability_score,
      })).sort((a, b) => b.score - a.score);
      return { donors: donors.slice(0, 15) };
    }
  },

  async sendChatMessage(message: string): Promise<any> {
    try {
      return await request("/ai/chat", {
        method: "POST",
        body: JSON.stringify({ message }),
      });
    } catch {
      return {
        response: `Thalassemia carrier screening (HPLC test) checks for abnormal hemoglobin fractions. If you are a carrier (HbA2 > 3.5%), it is healthy, but screening your partner protects against Thalassemia Major births.`,
        sources: ["Carrier Screening", "Thalassemia Prevention"]
      };
    }
  },

  // Transfusion Requests
  async requestTransfusion(patientId: string, quantity: number = 1.0): Promise<any> {
    try {
      return await request("/transfusion/request", {
        method: "POST",
        body: JSON.stringify({ patient_id: patientId, quantity_units: quantity }),
      });
    } catch {
      const patient = MOCK_PATIENTS.find(p => p.id === patientId) || MOCK_PATIENTS[0];
      const match = MOCK_DONORS.find(d => d.blood_group === patient.blood_group) || MOCK_DONORS[0];
      const workflowId = `tx-mock-${Math.floor(Math.random() * 90000 + 10000)}`;
      
      const timeline = [
        { step: "Request Created", status: "Success", message: `Transfusion request of ${quantity} units registered for ${patient.name}.`, timestamp: new Date().toISOString() },
        { step: "Find Donors", status: "Success", message: `Found compatible donors for blood group ${patient.blood_group}.`, timestamp: new Date().toISOString() },
        { step: "Rank Donors", status: "Success", message: `Smart matching ranked donor ${match.name} as top recommendation.`, timestamp: new Date().toISOString() },
        { step: "Outreach Sent", status: "In Progress", message: `Outreach notification dispatched to donor ${match.name}. Awaiting confirmation.`, timestamp: new Date().toISOString() }
      ];

      const wf = {
        workflow_id: workflowId,
        patient_id: patientId,
        status: "Outreach Sent",
        current_step: "Outreach Sent",
        assigned_donor_id: match.id,
        outreach_sent: true,
        response_received: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        timeline: timeline,
      };
      
      MOCK_WORKFLOWS[workflowId] = wf;
      return wf;
    }
  },

  async getTransfusionWorkflow(workflowId: string): Promise<any> {
    try {
      return await request(`/transfusion/workflow/${workflowId}`);
    } catch {
      return MOCK_WORKFLOWS[workflowId] || Object.values(MOCK_WORKFLOWS)[0];
    }
  },

  async respondTransfusionWorkflow(workflowId: string, accept: boolean): Promise<any> {
    try {
      return await request(`/transfusion/workflow/${workflowId}/respond?accept=${accept}`, {
        method: "POST"
      });
    } catch {
      const wf = MOCK_WORKFLOWS[workflowId];
      if (wf) {
        const status = accept ? "Completed" : "Failed";
        const step = accept ? "Schedule Donation" : "Failed";
        wf.status = status;
        wf.current_step = step;
        wf.response_received = accept ? "Accepted" : "Declined";
        wf.timeline.push({
          step: step,
          status: accept ? "Success" : "Failed",
          message: accept ? "Donor confirmed appointment. Donation scheduled." : "Donor declined outreach. Loop halted.",
          timestamp: new Date().toISOString()
        });
        return wf;
      }
      throw new Error("Workflow session not found");
    }
  },

  async getDashboardData(): Promise<any> {
    try {
      return await request("/analytics/dashboard");
    } catch {
      return {
        summary: {
          total_patients: MOCK_PATIENTS.length,
          total_donors: MOCK_DONORS.length,
          active_donors: MOCK_DONORS.filter(d => d.active_status === "Active").length,
          high_risk_patients: MOCK_PATIENTS.filter(p => p.risk_level === "HIGH").length,
          upcoming_transfusions: 12,
          ai_match_success_rate: 94.2
        },
        donation_trends: [
          { month: "Jan", donations: 45, shortages: 5 },
          { month: "Feb", donations: 52, shortages: 4 },
          { month: "Mar", donations: 58, shortages: 8 },
          { month: "Apr", donations: 63, shortages: 2 },
          { month: "May", donations: 71, shortages: 6 },
          { month: "Jun", donations: 84, shortages: 3 }
        ],
        blood_group_distribution: [
          { blood_group: "O Positive", count: 35 },
          { blood_group: "A Positive", count: 28 },
          { blood_group: "B Positive", count: 25 },
          { blood_group: "AB Positive", count: 12 },
          { blood_group: "O Negative", count: 8 },
          { blood_group: "A Negative", count: 6 },
        ],
        retention_trends: [
          { month: "Jan", retention_rate: 88.5, active_ratio: 78.2 },
          { month: "Feb", retention_rate: 89.2, active_ratio: 79.5 },
          { month: "Mar", retention_rate: 87.8, active_ratio: 80.1 },
          { month: "Apr", retention_rate: 91.0, active_ratio: 81.4 },
          { month: "May", retention_rate: 92.4, active_ratio: 83.2 },
          { month: "Jun", retention_rate: 93.1, active_ratio: 84.0 }
        ],
        forecasts: {
          demand_next_month: 145,
          supply_next_month: 120,
          shortage_risk: "MEDIUM",
          recommended_screening_location: "Bachupally, Hyderabad"
        }
      };
    }
  },
  async getBridgesOverview(): Promise<any[]> {
    try {
      return await request("/bridges/overview");
    } catch {
      return MOCK_BRIDGES;
    }
  },
  async toggleDonorConsent(id: string, consent: boolean): Promise<any> {
    try {
      return await request(`/donors/${id}/consent?consent=${consent}`, {
        method: "POST"
      });
    } catch {
      return { status: "success", donor_id: id, consent_given: consent };
    }
  },
  async runCareCoordinationCheck(): Promise<any> {
    try {
      return await request("/notifications/check-transfusions", {
        method: "POST"
      });
    } catch {
      return { status: "success", triggered_count: 0, triggered_workflows: [] };
    }
  }
};

const MOCK_BRIDGES = [
  {
    patient_id: "pat-1001",
    patient_name: "Rahul Deshmukh",
    blood_group: "O Positive",
    city: "Hyderabad",
    expected_next_transfusion_date: "04-06-2026",
    quantity_required: 2.0,
    risk_level: "HIGH",
    bridge_donors: [
      { id: "dnr-2001", name: "Aditya Sharma", phone: "+91 98765 43210", blood_group: "O Positive", city: "Hyderabad", last_donation_date: "10-02-2026", next_eligible_date: "10-05-2026", active_status: "Active", consent_given: true, match_score: 0.95 },
      { id: "dnr-2006", name: "Divya Das", phone: "+91 95678 90123", blood_group: "O Positive", city: "Hyderabad", last_donation_date: "12-05-2026", next_eligible_date: "12-08-2026", active_status: "Active", consent_given: true, match_score: 0.82 }
    ]
  },
  {
    patient_id: "pat-1002",
    patient_name: "Anjali Verma",
    blood_group: "A Positive",
    city: "Nizamabad",
    expected_next_transfusion_date: "08-06-2026",
    quantity_required: 1.5,
    risk_level: "MEDIUM",
    bridge_donors: [
      { id: "dnr-2002", name: "Sneha Reddy", phone: "+91 91234 56789", blood_group: "A Positive", city: "Hyderabad", last_donation_date: "15-03-2026", next_eligible_date: "15-06-2026", active_status: "Active", consent_given: true, match_score: 0.91 }
    ]
  }
];

// --- CLIENT-SIDE FALLBACK MOCK DATASETS ---
const MOCK_PATIENTS: Patient[] = [
  { id: "pat-1001", name: "Rahul Deshmukh", blood_group: "O Positive", city: "Hyderabad", quantity_required: 2.0, last_transfusion_date: "14-05-2026", expected_next_transfusion_date: "04-06-2026", risk_level: "HIGH", created_at: "2026-01-15T00:00:00Z" },
  { id: "pat-1002", name: "Anjali Verma", blood_group: "A Positive", city: "Nizamabad", quantity_required: 1.5, last_transfusion_date: "18-05-2026", expected_next_transfusion_date: "08-06-2026", risk_level: "MEDIUM", created_at: "2026-02-10T00:00:00Z" },
  { id: "pat-1003", name: "Kiran Pillai", blood_group: "B Positive", city: "Warangal", quantity_required: 1.0, last_transfusion_date: "22-05-2026", expected_next_transfusion_date: "12-06-2026", risk_level: "LOW", created_at: "2026-03-05T00:00:00Z" },
  { id: "pat-1004", name: "Priya Das", blood_group: "AB Positive", city: "Hyderabad", quantity_required: 2.5, last_transfusion_date: "12-05-2026", expected_next_transfusion_date: "02-06-2026", risk_level: "HIGH", created_at: "2026-01-20T00:00:00Z" },
  { id: "pat-1005", name: "Sanjay Grover", blood_group: "O Negative", city: "Karimnagar", quantity_required: 1.5, last_transfusion_date: "25-05-2026", expected_next_transfusion_date: "15-06-2026", risk_level: "MEDIUM", created_at: "2026-04-12T00:00:00Z" },
];

const MOCK_DONORS: Donor[] = [
  { id: "dnr-2001", name: "Aditya Sharma", phone: "+91 98765 43210", email: "aditya_sharma@example.com", blood_group: "O Positive", city: "Hyderabad", latitude: 17.395, longitude: 78.461, age: 28, gender: "Male", donor_type: "Regular", donations_till_date: 8, last_donation_date: "10-02-2026", next_eligible_date: "10-05-2026", engagement_score: 92.5, availability_score: 0.95, churn_risk: 0.08, active_status: "Active", created_at: "2025-05-10T00:00:00Z", updated_at: "2026-05-10T00:00:00Z" },
  { id: "dnr-2002", name: "Sneha Reddy", phone: "+91 91234 56789", email: "sneha_reddy@example.com", blood_group: "A Positive", city: "Hyderabad", latitude: 17.391, longitude: 78.455, age: 24, gender: "Female", donor_type: "Regular", donations_till_date: 5, last_donation_date: "15-03-2026", next_eligible_date: "15-06-2026", engagement_score: 85.0, availability_score: 0.88, churn_risk: 0.12, active_status: "Active", created_at: "2025-07-20T00:00:00Z", updated_at: "2026-05-15T00:00:00Z" },
  { id: "dnr-2003", name: "Vikram Kumar", phone: "+91 92345 67890", email: "vikram_kumar@example.com", blood_group: "B Positive", city: "Warangal", latitude: 17.969, longitude: 79.594, age: 35, gender: "Male", donor_type: "Regular", donations_till_date: 12, last_donation_date: "01-04-2026", next_eligible_date: "01-07-2026", engagement_score: 96.0, availability_score: 0.92, churn_risk: 0.04, active_status: "Active", created_at: "2025-01-15T00:00:00Z", updated_at: "2026-05-20T00:00:00Z" },
  { id: "dnr-2004", name: "Riya Mehta", phone: "+91 93456 78901", email: "riya_mehta@example.com", blood_group: "AB Positive", city: "Nizamabad", latitude: 18.672, longitude: 78.094, age: 31, gender: "Female", donor_type: "One-Time", donations_till_date: 2, last_donation_date: "20-04-2026", next_eligible_date: "20-07-2026", engagement_score: 45.0, availability_score: 0.65, churn_risk: 0.38, active_status: "Active", created_at: "2025-11-10T00:00:00Z", updated_at: "2026-04-20T00:00:00Z" },
  { id: "dnr-2005", name: "Sunil Grover", phone: "+91 94567 89012", email: "sunil_grover@example.com", blood_group: "O Negative", city: "Karimnagar", latitude: 18.438, longitude: 79.128, age: 42, gender: "Male", donor_type: "Regular", donations_till_date: 10, last_donation_date: "05-01-2026", next_eligible_date: "05-04-2026", engagement_score: 74.5, availability_score: 0.78, churn_risk: 0.18, active_status: "Active", created_at: "2025-03-01T00:00:00Z", updated_at: "2026-05-05T00:00:00Z" },
  { id: "dnr-2006", name: "Divya Das", phone: "+91 95678 90123", email: "divya_das@example.com", blood_group: "O Positive", city: "Hyderabad", latitude: 17.387, longitude: 78.476, age: 27, gender: "Female", donor_type: "Regular", donations_till_date: 3, last_donation_date: "12-05-2026", next_eligible_date: "12-08-2026", engagement_score: 60.0, availability_score: 0.45, churn_risk: 0.52, active_status: "Active", created_at: "2025-09-05T00:00:00Z", updated_at: "2026-05-12T00:00:00Z" }
];

const MOCK_WORKFLOWS: Record<string, any> = {
  "tx-mock-12345": {
    workflow_id: "tx-mock-12345",
    patient_id: "pat-1001",
    status: "Outreach Sent",
    current_step: "Outreach Sent",
    assigned_donor_id: "dnr-2001",
    outreach_sent: true,
    response_received: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    timeline: [
      { step: "Request Created", status: "Success", message: "Transfusion request registered for Rahul Deshmukh.", timestamp: new Date().toISOString() },
      { step: "Find Donors", status: "Success", message: "Found 4 compatible O Positive donors.", timestamp: new Date().toISOString() },
      { step: "Rank Donors", status: "Success", message: "Aditya Sharma ranked as top match (Score: 97.8%).", timestamp: new Date().toISOString() },
      { step: "Outreach Sent", status: "In Progress", message: "Outreach message dispatched via WhatsApp. Waiting for response.", timestamp: new Date().toISOString() }
    ]
  }
};
