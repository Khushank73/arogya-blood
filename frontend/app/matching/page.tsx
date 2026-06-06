"use client";

import { useEffect, useState } from "react";
import { useStore } from "@/store/useStore";
import { apiService, Patient } from "@/services/api";
import { 
  Compass, 
  MapPin, 
  Sparkles, 
  Activity, 
  CheckCircle,
  HelpCircle,
  Clock,
  Send,
  Calendar,
  AlertCircle
} from "lucide-react";

export default function MatchingPage() {
  const { patients, fetchPatients, requestTransfusion, activeWorkflow, isLoading } = useStore();
  const [selectedPatientId, setSelectedPatientId] = useState<string>("");
  const [matches, setMatches] = useState<any[]>([]);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [outreachSuccess, setOutreachSuccess] = useState<string | null>(null);

  useEffect(() => {
    fetchPatients();
  }, [fetchPatients]);

  const handlePatientChange = async (patientId: string) => {
    setSelectedPatientId(patientId);
    if (!patientId) {
      setMatches([]);
      return;
    }
    setLoadingMatches(true);
    setOutreachSuccess(null);
    try {
      const matchRes = await apiService.getTopMatches(patientId);
      setMatches(matchRes.recommendations || []);
    } catch (err) {
      setMatches([]);
    } finally {
      setLoadingMatches(false);
    }
  };

  const handleTriggerWorkflow = async () => {
    if (!selectedPatientId) return;
    try {
      const wId = await requestTransfusion(selectedPatientId, 1.0);
      setOutreachSuccess(`Transfusion workflow ${wId} successfully initialized! Top donor selected and notified.`);
    } catch (err) {
      alert("Error starting transfusion workflow.");
    }
  };

  const selectedPatient = patients.find(p => p.id === selectedPatientId);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Header */}
      <div>
        <h2 className="text-3xl font-bold font-heading text-slate-100 tracking-tight">Smart Matching Engine</h2>
        <p className="text-slate-400 text-sm">Coordinate biological compatibility, geodistance parameters, and availability indexes to secure Care Bridges.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Selection panel */}
        <div className="glass-panel p-6 rounded-2xl space-y-6">
          <h3 className="text-lg font-bold font-heading text-slate-100 flex items-center gap-2">
            <Compass className="w-5 h-5 text-rose-500" />
            Bridges Coordinator
          </h3>

          <div className="space-y-2">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">Select Patient Profile</label>
            <select
              value={selectedPatientId}
              onChange={(e) => handlePatientChange(e.target.value)}
              className="w-full px-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition text-sm font-semibold"
            >
              <option value="">-- Choose Patient --</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.blood_group})</option>
              ))}
            </select>
          </div>

          {selectedPatient && (
            <div className="p-4 bg-slate-950/40 rounded-xl border border-slate-800 space-y-3 text-xs font-semibold text-slate-300">
              <h4 className="text-slate-400 uppercase tracking-wider">Patient Details</h4>
              <div className="flex justify-between border-b border-slate-800/60 pb-2">
                <span>Blood Group:</span>
                <span className="text-rose-500 font-bold">{selectedPatient.blood_group}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/60 pb-2">
                <span>Quantity Required:</span>
                <span className="text-slate-200">{selectedPatient.quantity_required} Units</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/60 pb-2">
                <span>Target City:</span>
                <span className="text-slate-200">{selectedPatient.city}</span>
              </div>
              <div className="flex justify-between">
                <span>Risk Level:</span>
                <span className={selectedPatient.risk_level === "HIGH" ? "text-red-500" : selectedPatient.risk_level === "MEDIUM" ? "text-amber-500" : "text-emerald-500"}>
                  {selectedPatient.risk_level}
                </span>
              </div>
            </div>
          )}

          {selectedPatient && (
            <div className="space-y-3">
              <button
                onClick={handleTriggerWorkflow}
                className="w-full flex items-center justify-center gap-2 py-3 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl shadow-glass-primary transition duration-200 text-sm"
              >
                <Send className="w-4 h-4" />
                Initialize Outreach Workflow
              </button>
              <p className="text-[10px] text-slate-500 font-medium text-center leading-relaxed">
                Triggers the LangGraph state machine workflow: Finding compatibility, ranking records, and dispatching automated outreach.
              </p>
            </div>
          )}

          {outreachSuccess && (
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs font-semibold rounded-xl flex items-start gap-2">
              <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{outreachSuccess}</span>
            </div>
          )}
        </div>

        {/* Matches lists panel */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-panel p-6 rounded-2xl">
            <div className="flex items-center justify-between mb-6 border-b border-slate-800/80 pb-4">
              <div>
                <h3 className="text-lg font-bold font-heading text-slate-100">Recommended Matches</h3>
                <p className="text-xs text-slate-400">Top 10 compatible blood donors ranked using AI Smart Match composite model.</p>
              </div>
              <div className="text-xs text-slate-500 font-bold uppercase tracking-wider bg-slate-900 px-3 py-1.5 rounded-xl border border-slate-800">
                Formula: 40-20-20-10-10
              </div>
            </div>

            {loadingMatches ? (
              <div className="text-center py-12 text-sm text-slate-500 font-medium">
                Querrying XGBoost donor availability and calculating Haversine geodistances...
              </div>
            ) : !selectedPatientId ? (
              <div className="text-center py-12 text-slate-500 text-sm font-medium border-2 border-dashed border-slate-800 rounded-2xl flex flex-col items-center gap-2">
                <Compass className="w-8 h-8 text-slate-600" />
                Please select a patient profile on the left to compute matches.
              </div>
            ) : matches.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-sm font-medium border-2 border-dashed border-slate-800 rounded-2xl flex flex-col items-center gap-2">
                <AlertCircle className="w-8 h-8 text-rose-600" />
                No eligible matching donors found for blood group {selectedPatient?.blood_group}.
              </div>
            ) : (
              <div className="space-y-4">
                {matches.map((item, index) => {
                  const matchPct = Math.round(item.match_score * 100);
                  const availPct = Math.round(item.availability_score * 100);
                  return (
                    <div 
                      key={item.donor_id}
                      className="p-5 bg-slate-900/30 border border-slate-800/80 rounded-2xl hover:border-rose-500/30 transition duration-200 flex flex-col md:flex-row md:items-center justify-between gap-5"
                    >
                      {/* Left Block */}
                      <div className="space-y-2 flex-1">
                        <div className="flex items-center gap-3">
                          <span className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-800 text-slate-400 text-xs font-bold">
                            {index + 1}
                          </span>
                          <h4 className="font-bold text-slate-100">{item.name}</h4>
                          <span className="px-2 py-0.5 bg-rose-500/10 text-rose-500 text-[10px] font-bold rounded-lg uppercase tracking-wide border border-rose-500/10">
                            {item.blood_group}
                          </span>
                        </div>
                        
                        {/* Parameter list */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                          <div className="flex items-center gap-1">
                            <MapPin className="w-3.5 h-3.5 text-slate-400" />
                            <span>{item.distance_km} km away</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5 text-slate-400" />
                            <span>Avail: {availPct}%</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Activity className="w-3.5 h-3.5 text-slate-400" />
                            <span>Engage: {item.engagement_score}%</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <CheckCircle className="w-3.5 h-3.5 text-accent-success" />
                            <span className="text-accent-success">{item.eligibility}</span>
                          </div>
                        </div>
                      </div>

                      {/* Right Block Score meters */}
                      <div className="flex items-center gap-4 border-t md:border-t-0 pt-4 md:pt-0 border-slate-800/50">
                        {/* Metric gauges */}
                        <div className="w-[120px] space-y-1.5 text-[9px] font-bold text-slate-500 uppercase tracking-wider">
                          <div className="space-y-0.5">
                            <div className="flex justify-between">
                              <span>Availability</span>
                              <span>{availPct}%</span>
                            </div>
                            <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                              <div className="h-full bg-rose-500" style={{ width: `${availPct}%` }}></div>
                            </div>
                          </div>
                          <div className="space-y-0.5">
                            <div className="flex justify-between">
                              <span>Distance</span>
                              <span>{Math.round(Math.max(0, 100 - item.distance_km * 2))}%</span>
                            </div>
                            <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                              <div className="h-full bg-blue-500" style={{ width: `${Math.max(0, 100 - item.distance_km * 2)}%` }}></div>
                            </div>
                          </div>
                        </div>

                        {/* Large Score Indicator */}
                        <div className="text-center bg-slate-900 border border-slate-800 px-4 py-2.5 rounded-xl min-w-[95px]">
                          <span className="text-xs text-slate-500 font-bold block uppercase tracking-wider">Match Score</span>
                          <span className="text-lg font-bold font-heading text-rose-500">{matchPct}%</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
