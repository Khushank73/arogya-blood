"use client";

import { useEffect, useState } from "react";
import { useStore } from "@/store/useStore";
import { apiService, Patient } from "@/services/api";
import { 
  Users, 
  AlertTriangle, 
  Sparkles, 
  Activity, 
  Plus, 
  Trash2, 
  X,
  Droplet,
  Compass,
  Calendar,
  Layers
} from "lucide-react";

export default function PatientsPage() {
  const { patients, fetchPatients, addPatient, removePatient, isLoading } = useStore();
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [donorCircle, setDonorCircle] = useState<any[]>([]);
  const [loadingCircle, setLoadingCircle] = useState(false);
  const [isAddOpen, setIsAddOpen] = useState(false);

  // Form states
  const [name, setName] = useState("");
  const [bloodGroup, setBloodGroup] = useState("O Positive");
  const [city, setCity] = useState("Hyderabad");
  const [qty, setQty] = useState(1.5);
  const [lastTrans, setLastTrans] = useState("");
  const [nextTrans, setNextTrans] = useState("");

  useEffect(() => {
    fetchPatients();
  }, [fetchPatients]);

  const handleSelectPatient = async (p: Patient) => {
    setSelectedPatient(p);
    setLoadingCircle(true);
    try {
      const matchRes = await apiService.getTopMatches(p.id);
      setDonorCircle(matchRes.recommendations || []);
    } catch (err) {
      setDonorCircle([]);
    } finally {
      setLoadingCircle(false);
    }
  };

  const handleAddPatientSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await addPatient({
      name,
      blood_group: bloodGroup,
      city,
      quantity_required: qty,
      last_transfusion_date: lastTrans || undefined,
      expected_next_transfusion_date: nextTrans || undefined,
      risk_level: qty >= 2.0 ? "HIGH" : qty >= 1.5 ? "MEDIUM" : "LOW"
    });
    // Reset
    setName("");
    setQty(1.5);
    setLastTrans("");
    setNextTrans("");
    setIsAddOpen(false);
  };

  const handleDeletePatient = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("Are you sure you want to delete this patient profile?")) {
      await removePatient(id);
      if (selectedPatient?.id === id) {
        setSelectedPatient(null);
      }
    }
  };

  return (
    <div className="space-y-8 animate-fade-in relative min-h-[80vh]">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold font-heading text-slate-100 tracking-tight">Patient Coordination</h2>
          <p className="text-slate-400 text-sm">Monitor Thalassemia transfusion schedules, risk indexes, and compatible donor lists.</p>
        </div>
        <button 
          onClick={() => setIsAddOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-semibold rounded-xl shadow-glass-primary transition duration-200 text-sm"
        >
          <Plus className="w-4 h-4" />
          Register Patient
        </button>
      </div>

      {/* Grid Layout (Slides open details panel) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Table Container */}
        <div className={`glass-panel rounded-2xl overflow-hidden transition-all duration-300 ${
          selectedPatient ? "lg:col-span-7" : "lg:col-span-12"
        }`}>
          <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between">
            <h3 className="font-bold font-heading text-slate-100 text-sm uppercase tracking-wider">Patient Registry</h3>
            <span className="text-xs text-slate-500 font-semibold">{patients.length} Registered</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-xs font-semibold uppercase tracking-wider text-slate-500 bg-slate-950/20">
                  <th className="px-6 py-3">Patient Name</th>
                  <th className="px-6 py-3">Blood Group</th>
                  <th className="px-6 py-3">Next Transfusion</th>
                  <th className="px-6 py-3">Risk Level</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-sm">
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                      Loading patient directory...
                    </td>
                  </tr>
                ) : patients.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                      No patients registered. Add one to start.
                    </td>
                  </tr>
                ) : (
                  patients.map((p) => {
                    const isSelected = selectedPatient?.id === p.id;
                    return (
                      <tr 
                        key={p.id}
                        onClick={() => handleSelectPatient(p)}
                        className={`hover:bg-slate-800/30 cursor-pointer transition ${
                          isSelected ? "bg-rose-500/5 border-l-4 border-rose-600" : ""
                        }`}
                      >
                        <td className="px-6 py-4 font-semibold text-slate-200">{p.name}</td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-500/10 text-rose-500 text-xs font-bold border border-rose-500/10">
                            <Droplet className="w-3.5 h-3.5" />
                            {p.blood_group}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-slate-400 font-medium">
                          {p.expected_next_transfusion_date || "Not scheduled"}
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex px-2 py-0.5 text-xs font-bold rounded-full ${
                            p.risk_level === "HIGH" 
                              ? "bg-red-500/10 text-red-500 border border-red-500/20" 
                              : p.risk_level === "MEDIUM" 
                              ? "bg-amber-500/10 text-amber-500 border border-amber-500/20" 
                              : "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                          }`}>
                            {p.risk_level}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button 
                            onClick={(e) => handleDeletePatient(p.id, e)}
                            className="p-1 text-slate-500 hover:text-red-500 rounded-lg transition"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Patient Details Splitted Side Panel */}
        {selectedPatient && (
          <div className="lg:col-span-5 glass-panel rounded-2xl p-6 space-y-6 animate-fade-in">
            {/* Header */}
            <div className="flex items-start justify-between border-b border-slate-800/80 pb-4">
              <div>
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Patient Dossier</span>
                <h3 className="text-xl font-bold font-heading text-slate-100">{selectedPatient.name}</h3>
              </div>
              <button 
                onClick={() => setSelectedPatient(null)}
                className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Profile Info Grid */}
            <div className="grid grid-cols-2 gap-4 text-xs font-semibold">
              <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800/80">
                <span className="text-slate-500 uppercase block mb-1">Blood Group</span>
                <span className="text-sm font-bold text-rose-500">{selectedPatient.blood_group}</span>
              </div>
              <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800/80">
                <span className="text-slate-500 uppercase block mb-1">Risk Assessment</span>
                <span className={`text-sm font-bold flex items-center gap-1 ${
                  selectedPatient.risk_level === "HIGH" ? "text-red-500" : selectedPatient.risk_level === "MEDIUM" ? "text-amber-500" : "text-emerald-500"
                }`}>
                  {selectedPatient.risk_level === "HIGH" && <AlertTriangle className="w-4 h-4 animate-bounce" />}
                  {selectedPatient.risk_level} Risk
                </span>
              </div>
              <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800/80">
                <span className="text-slate-500 uppercase block mb-1">Required Volume</span>
                <span className="text-sm text-slate-200">{selectedPatient.quantity_required} Units</span>
              </div>
              <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800/80">
                <span className="text-slate-500 uppercase block mb-1">Target Location</span>
                <span className="text-sm text-slate-200">{selectedPatient.city || "Hyderabad"}</span>
              </div>
            </div>

            {/* AI Risk Assessment Card */}
            <div className="p-4 bg-rose-500/5 border border-rose-500/10 rounded-xl space-y-2">
              <div className="flex items-center gap-1.5 text-xs text-rose-500 font-bold uppercase tracking-wider">
                <Sparkles className="w-4 h-4" />
                AI Risk Assessment
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {selectedPatient.risk_level === "HIGH" 
                  ? "CRITICAL: High volume demands (>=2.0 units) paired with local supply shortages. Expected next transfusion date is urgent. Triggering automated donor matching and workflow coordinators alerts recommended."
                  : "STABLE: Standard 3-week replenishment cycle. Matching donor register contains active matching candidates. Monitor next eligible schedules."}
              </p>
            </div>

            {/* Donor Circle (Matches) */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                  <Compass className="w-4 h-4 text-rose-500" />
                  Donor Circle (Top Recommendations)
                </h4>
                <span className="text-[10px] text-slate-500 font-bold">Compatible Matches</span>
              </div>

              {loadingCircle ? (
                <div className="text-center py-4 text-xs text-slate-500">
                  Ranking matches via Smart Matching Engine...
                </div>
              ) : donorCircle.length === 0 ? (
                <div className="text-center py-4 text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
                  No active eligible matches found in database.
                </div>
              ) : (
                <div className="space-y-2.5 max-h-[220px] overflow-y-auto pr-1">
                  {donorCircle.map((donor) => (
                    <div 
                      key={donor.donor_id}
                      className="p-3 bg-slate-900/30 border border-slate-800/60 rounded-xl flex items-center justify-between text-xs hover:border-rose-600/30 transition duration-150"
                    >
                      <div className="space-y-0.5">
                        <div className="font-semibold text-slate-200">{donor.name}</div>
                        <div className="text-slate-500 font-medium">{donor.distance_km} km away • Availability: {Math.round(donor.availability_score * 100)}%</div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-rose-500">{Math.round(donor.match_score * 100)}% Match</div>
                        <span className="text-[9px] px-1.5 py-0.2 bg-emerald-500/10 text-emerald-500 rounded font-semibold uppercase">
                          {donor.eligibility}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* History logs timeline */}
            <div className="space-y-3 border-t border-slate-800/60 pt-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                <Calendar className="w-4 h-4 text-accent" />
                Transfusion Logs
              </h4>
              <div className="space-y-2 text-xs text-slate-400 font-medium">
                <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/20">
                  <span>Last Transfusion Date:</span>
                  <span className="text-slate-200">{selectedPatient.last_transfusion_date || "N/A"}</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/20">
                  <span>Expected Next Transfusion:</span>
                  <span className="text-rose-500 font-semibold">{selectedPatient.expected_next_transfusion_date || "N/A"}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modal Dialog for Registering Patient */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-lg rounded-2xl p-6 space-y-5 shadow-glass animate-fade-in">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold font-heading text-slate-100 flex items-center gap-2">
                <Users className="w-5 h-5 text-rose-500" />
                Register New Patient
              </h3>
              <button 
                onClick={() => setIsAddOpen(false)}
                className="text-slate-400 hover:text-slate-200 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddPatientSubmit} className="space-y-4 text-xs font-semibold text-slate-300">
              <div className="space-y-1">
                <label className="block text-slate-400 uppercase tracking-wider">Patient Full Name</label>
                <input 
                  type="text" 
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="E.g. Rahul Deshmukh"
                  className="w-full px-3 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="block text-slate-400 uppercase tracking-wider">Blood Group</label>
                  <select 
                    value={bloodGroup}
                    onChange={(e) => setBloodGroup(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition"
                  >
                    <option>O Positive</option>
                    <option>A Positive</option>
                    <option>B Positive</option>
                    <option>AB Positive</option>
                    <option>O Negative</option>
                    <option>A Negative</option>
                    <option>B Negative</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="block text-slate-400 uppercase tracking-wider">City</label>
                  <input 
                    type="text" 
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-1">
                  <label className="block text-slate-400 uppercase tracking-wider">Qty Required (Units)</label>
                  <input 
                    type="number" 
                    step="0.5" 
                    value={qty}
                    onChange={(e) => setQty(parseFloat(e.target.value))}
                    className="w-full px-3 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition"
                    min="0.5"
                    max="5.0"
                    required
                  />
                </div>
                <div className="space-y-1 col-span-2">
                  <label className="block text-slate-400 uppercase tracking-wider">Expected Next Transfusion</label>
                  <input 
                    type="text" 
                    value={nextTrans}
                    onChange={(e) => setNextTrans(e.target.value)}
                    placeholder="DD-MM-YYYY"
                    className="w-full px-3 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition"
                  />
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
                <button 
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold rounded-xl transition duration-150"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white font-semibold rounded-xl shadow-glass-primary transition duration-150"
                >
                  Register
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
