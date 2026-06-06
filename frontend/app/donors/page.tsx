"use client";

import { useEffect, useState } from "react";
import { useStore } from "@/store/useStore";
import { apiService, Donor } from "@/services/api";
import { 
  Droplet, 
  Clock, 
  Activity, 
  Trash2, 
  X, 
  Plus, 
  TrendingDown, 
  Smile, 
  ShieldCheck, 
  AlertTriangle,
  History,
  MessageSquare
} from "lucide-react";

export default function DonorsPage() {
  const { donors, fetchDonors, addDonor, removeDonor, isLoading } = useStore();
  const [selectedDonor, setSelectedDonor] = useState<Donor | null>(null);
  const [donationHistory, setDonationHistory] = useState<any[]>([]);
  const [outreachLogs, setOutreachLogs] = useState<any[]>([]);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [isAddOpen, setIsAddOpen] = useState(false);

  // Form states
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [bloodGroup, setBloodGroup] = useState("O Positive");
  const [city, setCity] = useState("Hyderabad");
  const [age, setAge] = useState(25);
  const [gender, setGender] = useState("Male");
  const [type, setType] = useState("Regular");

  useEffect(() => {
    fetchDonors();
  }, [fetchDonors]);

  const handleSelectDonor = async (d: Donor) => {
    setSelectedDonor(d);
    setLoadingDetails(true);
    // In a real environment, we'd query the DB for this donor's specific logs.
    // We can simulate them or query mock API responses.
    try {
      // Mock history logs for selected donor
      const randHist = [
        { date: d.last_donation_date || "10-02-2026", status: "Completed", notes: "Whole Blood donation" },
        { date: "15-11-2025", status: "Completed", notes: "Regular donation camp" }
      ];
      const randOut = [
        { date: "02-06-2026", channel: "WhatsApp", message: "Are you available to donate?", response: "Accepted" },
        { date: "18-05-2026", channel: "WhatsApp", message: "Upcoming blood bridge match", response: "No Response" }
      ];
      setDonationHistory(randHist);
      setOutreachLogs(randOut);
    } catch {
      setDonationHistory([]);
      setOutreachLogs([]);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleAddDonorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await addDonor({
      name,
      phone,
      email,
      blood_group: bloodGroup,
      city,
      age,
      gender,
      donor_type: type,
      engagement_score: 80.0,
      active_status: "Active"
    });
    // Reset
    setName("");
    setPhone("");
    setEmail("");
    setIsAddOpen(false);
  };

  const handleDeleteDonor = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("Are you sure you want to remove this donor profile?")) {
      await removeDonor(id);
      if (selectedDonor?.id === id) {
        setSelectedDonor(null);
      }
    }
  };

  return (
    <div className="space-y-8 animate-fade-in relative min-h-[80vh]">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold font-heading text-slate-100 tracking-tight">Blood Donors Register</h2>
          <p className="text-slate-400 text-sm">Automate donor records, analyze churn risks, and manage availability scores.</p>
        </div>
        <button 
          onClick={() => setIsAddOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-semibold rounded-xl shadow-glass-primary transition duration-200 text-sm"
        >
          <Plus className="w-4 h-4" />
          Add Donor
        </button>
      </div>

      {/* Grid Layout (Slides open details panel) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Table Container */}
        <div className={`glass-panel rounded-2xl overflow-hidden transition-all duration-300 ${
          selectedDonor ? "lg:col-span-7" : "lg:col-span-12"
        }`}>
          <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between">
            <h3 className="font-bold font-heading text-slate-100 text-sm uppercase tracking-wider">Donor List</h3>
            <span className="text-xs text-slate-500 font-semibold">{donors.length} Profiles</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-xs font-semibold uppercase tracking-wider text-slate-500 bg-slate-950/20">
                  <th className="px-6 py-3">Donor Name</th>
                  <th className="px-6 py-3">Blood Group</th>
                  <th className="px-6 py-3">Availability</th>
                  <th className="px-6 py-3">Churn Risk</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-sm">
                {isLoading ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                      Loading donor registry...
                    </td>
                  </tr>
                ) : donors.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                      No donors found. Add one to start.
                    </td>
                  </tr>
                ) : (
                  donors.map((d) => {
                    const isSelected = selectedDonor?.id === d.id;
                    const availPct = Math.round(d.availability_score * 100);
                    const churnPct = Math.round(d.churn_risk * 100);

                    return (
                      <tr 
                        key={d.id}
                        onClick={() => handleSelectDonor(d)}
                        className={`hover:bg-slate-800/30 cursor-pointer transition ${
                          isSelected ? "bg-rose-500/5 border-l-4 border-rose-600" : ""
                        }`}
                      >
                        <td className="px-6 py-4 font-semibold text-slate-200">{d.name}</td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-500/10 text-rose-500 text-xs font-bold border border-rose-500/10">
                            <Droplet className="w-3.5 h-3.5" />
                            {d.blood_group}
                          </span>
                        </td>
                        <td className="px-6 py-4 font-medium">
                          <span className={availPct > 70 ? "text-accent-success" : availPct > 40 ? "text-accent-warning" : "text-accent-danger"}>
                            {availPct}%
                          </span>
                        </td>
                        <td className="px-6 py-4 font-medium">
                          <span className={churnPct < 25 ? "text-accent-success" : churnPct < 55 ? "text-accent-warning" : "text-accent-danger"}>
                            {churnPct}%
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex px-2 py-0.5 text-xs font-bold rounded-full ${
                            d.active_status === "Active" 
                              ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" 
                              : "bg-slate-500/10 text-slate-500 border border-slate-500/20"
                          }`}>
                            {d.active_status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button 
                            onClick={(e) => handleDeleteDonor(d.id, e)}
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

        {/* Selected Donor Split Analyzer */}
        {selectedDonor && (
          <div className="lg:col-span-5 glass-panel rounded-2xl p-6 space-y-6 animate-fade-in">
            {/* Header */}
            <div className="flex items-start justify-between border-b border-slate-800 pb-4">
              <div>
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Donor Profile</span>
                <h3 className="text-xl font-bold font-heading text-slate-100">{selectedDonor.name}</h3>
              </div>
              <button 
                onClick={() => setSelectedDonor(null)}
                className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Profile Info Grid */}
            <div className="grid grid-cols-2 gap-4 text-xs font-semibold">
              <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800/80">
                <span className="text-slate-500 uppercase block mb-1">Blood Group</span>
                <span className="text-sm font-bold text-rose-500">{selectedDonor.blood_group}</span>
              </div>
              <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800/80">
                <span className="text-slate-500 uppercase block mb-1">Status</span>
                <span className={`text-sm font-bold flex items-center gap-1 ${
                  selectedDonor.active_status === "Active" ? "text-emerald-500" : "text-slate-500"
                }`}>
                  <ShieldCheck className="w-4 h-4" />
                  {selectedDonor.active_status}
                </span>
              </div>
              <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800/80">
                <span className="text-slate-500 uppercase block mb-1">Phone</span>
                <span className="text-sm text-slate-200">{selectedDonor.phone || "N/A"}</span>
              </div>
              <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800/80">
                <span className="text-slate-500 uppercase block mb-1">City</span>
                <span className="text-sm text-slate-200">{selectedDonor.city || "Hyderabad"}</span>
              </div>
            </div>

            {/* ML Analytics Cards */}
            <div className="grid grid-cols-2 gap-4">
              {/* Availability Score (XGBoost) */}
              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-800 space-y-1">
                <div className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Availability Index</div>
                <h4 className="text-2xl font-bold font-heading text-slate-100">
                  {Math.round(selectedDonor.availability_score * 100)}%
                </h4>
                <div className="text-[9px] text-slate-400 font-semibold">
                  Model: <span className="text-rose-500">XGBoost Regressor</span>
                </div>
              </div>

              {/* Churn Risk (RandomForest) */}
              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-800 space-y-1">
                <div className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Churn Risk Probability</div>
                <h4 className={`text-2xl font-bold font-heading ${
                  selectedDonor.churn_risk > 0.5 ? "text-accent-danger" : selectedDonor.churn_risk > 0.25 ? "text-accent-warning" : "text-accent-success"
                }`}>
                  {Math.round(selectedDonor.churn_risk * 100)}%
                </h4>
                <div className="text-[9px] text-slate-400 font-semibold">
                  Model: <span className="text-indigo-400">RandomForest</span>
                </div>
              </div>
            </div>

            {/* Engagement and predictive indicators summary */}
            <div className="p-4 bg-rose-500/5 border border-rose-500/10 rounded-xl space-y-2">
              <div className="flex items-center gap-1.5 text-xs text-rose-500 font-bold uppercase tracking-wider">
                <TrendingDown className="w-4 h-4" />
                Retentive Insights
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {selectedDonor.churn_risk > 0.5
                  ? "Donor shows high markers of inactivity: last donation was >120 days ago and reply rates have declined. Action: Schedule manual check-in or send a gratitude card."
                  : "Donor displays steady active markers: high engagement score and reliable contact log reply rates. No retention action necessary."}
              </p>
            </div>

            {/* Donation History */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                <History className="w-4 h-4 text-accent" />
                Donation History ({selectedDonor.donations_till_date} total)
              </h4>
              
              {loadingDetails ? (
                <div className="text-center py-2 text-xs text-slate-500">Loading history...</div>
              ) : (
                <div className="space-y-2 max-h-[150px] overflow-y-auto">
                  {donationHistory.map((item, index) => (
                    <div key={index} className="p-2.5 bg-slate-900/40 rounded-lg text-xs flex items-center justify-between">
                      <span className="font-semibold text-slate-200">{item.date}</span>
                      <span className="text-slate-400">{item.notes}</span>
                      <span className="px-1.5 py-0.2 bg-emerald-500/10 text-emerald-500 font-semibold uppercase rounded text-[9px]">
                        {item.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Outreach Logs */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                <MessageSquare className="w-4 h-4 text-accent-success" />
                Communication Logs
              </h4>
              <div className="space-y-2">
                {outreachLogs.map((log, index) => (
                  <div key={index} className="p-2.5 bg-slate-900/40 rounded-lg text-xs space-y-1">
                    <div className="flex items-center justify-between text-slate-500 font-semibold">
                      <span>{log.date} via {log.channel}</span>
                      <span className={log.response === "Accepted" ? "text-accent-success" : "text-accent-danger"}>{log.response}</span>
                    </div>
                    <p className="text-slate-300 text-[11px] italic">"{log.message}"</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modal Dialog for Adding Donor */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/80 backdrop-blur-sm overflow-y-auto p-4 md:p-10">
          <div className="glass-panel w-full max-w-lg rounded-2xl p-6 space-y-5 shadow-glass animate-fade-in my-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold font-heading text-slate-100 flex items-center gap-2">
                <Droplet className="w-5 h-5 text-rose-500 animate-pulse" />
                Add New Blood Donor
              </h3>
              <button 
                onClick={() => setIsAddOpen(false)}
                className="text-slate-400 hover:text-slate-200 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddDonorSubmit} className="space-y-4 text-xs font-semibold text-slate-300">
              <div className="space-y-1">
                <label className="block text-slate-400 uppercase tracking-wider">Donor Full Name</label>
                <input 
                  type="text" 
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="E.g. Vikram Kumar"
                  className="w-full px-3 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="block text-slate-400 uppercase tracking-wider">Phone Number</label>
                  <input 
                    type="text" 
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+91 XXXXX XXXXX"
                    className="w-full px-3 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition"
                    required
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-slate-400 uppercase tracking-wider">Email Address</label>
                  <input 
                    type="email" 
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="email@example.com"
                    className="w-full px-3 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
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

                <div className="space-y-1">
                  <label className="block text-slate-400 uppercase tracking-wider">Donor Type</label>
                  <select 
                    value={type}
                    onChange={(e) => setType(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition"
                  >
                    <option>Regular</option>
                    <option>One-Time</option>
                    <option>Emergency</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="block text-slate-400 uppercase tracking-wider">Age</label>
                  <input 
                    type="number" 
                    value={age}
                    onChange={(e) => setAge(parseInt(e.target.value))}
                    className="w-full px-3 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition"
                    min="18"
                    max="65"
                    required
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-slate-400 uppercase tracking-wider">Gender</label>
                  <select 
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition"
                  >
                    <option>Male</option>
                    <option>Female</option>
                  </select>
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
                  Save Profile
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
