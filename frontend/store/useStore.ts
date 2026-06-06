import { create } from 'zustand';
import { apiService, Patient, Donor } from '../services/api';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  sources?: string[];
}

interface StateStore {
  patients: Patient[];
  donors: Donor[];
  dashboard: any;
  activeWorkflow: any;
  chatHistory: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  lastSyncTime: string | null;
  
  // Actions
  fetchPatients: () => Promise<void>;
  fetchDonors: () => Promise<void>;
  fetchDashboard: () => Promise<void>;
  
  addPatient: (patient: Partial<Patient>) => Promise<void>;
  updatePatient: (id: string, patient: Partial<Patient>) => Promise<void>;
  removePatient: (id: string) => Promise<void>;
  
  addDonor: (donor: Partial<Donor>) => Promise<void>;
  updateDonor: (id: string, donor: Partial<Donor>) => Promise<void>;
  removeDonor: (id: string) => Promise<void>;
  
  requestTransfusion: (patientId: string, quantity: number) => Promise<string>;
  submitOutreachResponse: (workflowId: string, accept: boolean) => Promise<void>;
  fetchWorkflowStatus: (workflowId: string) => Promise<void>;
  
  sendMessage: (text: string) => Promise<void>;
  clearChat: () => void;
}

export const useStore = create<StateStore>((set, get) => ({
  patients: [],
  donors: [],
  dashboard: null,
  activeWorkflow: null,
  chatHistory: [
    {
      id: 'welcome',
      sender: 'assistant',
      text: 'Hello! I am the Blood Warriors Awareness Assistant. Ask me anything about Thalassemia, screening drives, pre-marital tests, or blood donation eligibility.',
      timestamp: new Date().toISOString()
    }
  ],
  isLoading: false,
  error: null,
  lastSyncTime: null,

  fetchPatients: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await apiService.getPatients();
      set({ patients: data, isLoading: false, lastSyncTime: new Date().toLocaleTimeString() });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  fetchDonors: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await apiService.getDonors();
      set({ donors: data, isLoading: false, lastSyncTime: new Date().toLocaleTimeString() });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  fetchDashboard: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await apiService.getDashboardData();
      set({ dashboard: data, isLoading: false, lastSyncTime: new Date().toLocaleTimeString() });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  addPatient: async (patient) => {
    try {
      const newPatient = await apiService.createPatient(patient);
      set((state) => ({ patients: [newPatient, ...state.patients], lastSyncTime: new Date().toLocaleTimeString() }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  updatePatient: async (id, patient) => {
    try {
      const updated = await apiService.updatePatient(id, patient);
      set((state) => ({
        patients: state.patients.map((p) => (p.id === id ? updated : p)),
        lastSyncTime: new Date().toLocaleTimeString()
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  removePatient: async (id) => {
    try {
      await apiService.deletePatient(id);
      set((state) => ({
        patients: state.patients.filter((p) => p.id !== id),
        lastSyncTime: new Date().toLocaleTimeString()
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  addDonor: async (donor) => {
    try {
      const newDonor = await apiService.createDonor(donor);
      set((state) => ({ donors: [newDonor, ...state.donors], lastSyncTime: new Date().toLocaleTimeString() }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  updateDonor: async (id, donor) => {
    try {
      const updated = await apiService.updateDonor(id, donor);
      set((state) => ({
        donors: state.donors.map((d) => (d.id === id ? updated : d)),
        lastSyncTime: new Date().toLocaleTimeString()
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  removeDonor: async (id) => {
    try {
      await apiService.deleteDonor(id);
      set((state) => ({
        donors: state.donors.filter((d) => d.id !== id),
        lastSyncTime: new Date().toLocaleTimeString()
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  requestTransfusion: async (patientId, quantity) => {
    set({ isLoading: true, error: null });
    try {
      const wf = await apiService.requestTransfusion(patientId, quantity);
      set({ activeWorkflow: wf, isLoading: false, lastSyncTime: new Date().toLocaleTimeString() });
      return wf.workflow_id;
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
      throw err;
    }
  },

  submitOutreachResponse: async (workflowId, accept) => {
    set({ isLoading: true, error: null });
    try {
      const updatedWf = await apiService.respondTransfusionWorkflow(workflowId, accept);
      set({ activeWorkflow: updatedWf, isLoading: false, lastSyncTime: new Date().toLocaleTimeString() });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  fetchWorkflowStatus: async (workflowId) => {
    try {
      const wf = await apiService.getTransfusionWorkflow(workflowId);
      set({ activeWorkflow: wf, lastSyncTime: new Date().toLocaleTimeString() });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  sendMessage: async (text) => {
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}-1`,
      sender: 'user',
      text,
      timestamp: new Date().toISOString()
    };
    
    set((state) => ({ chatHistory: [...state.chatHistory, userMsg] }));
    
    try {
      const chatRes = await apiService.sendChatMessage(text);
      const botMsg: ChatMessage = {
        id: `msg-${Date.now()}-2`,
        sender: 'assistant',
        text: chatRes.response,
        timestamp: new Date().toISOString(),
        sources: chatRes.sources
      };
      set((state) => ({ chatHistory: [...state.chatHistory, botMsg] }));
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `msg-${Date.now()}-error`,
        sender: 'assistant',
        text: 'Sorry, I encountered an error communicating with the awareness engine.',
        timestamp: new Date().toISOString()
      };
      set((state) => ({ chatHistory: [...state.chatHistory, errorMsg] }));
    }
  },

  clearChat: () => {
    set({
      chatHistory: [
        {
          id: 'welcome',
          sender: 'assistant',
          text: 'Hello! I am the Blood Warriors Awareness Assistant. Ask me anything about Thalassemia, screening drives, pre-marital tests, or blood donation eligibility.',
          timestamp: new Date().toISOString()
        }
      ]
    });
  }
}));
