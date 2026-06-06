"use client";

import { useState } from "react";
import { 
  Settings, 
  Server, 
  ShieldCheck, 
  ToggleLeft,
  ToggleRight,
  Database,
  CloudLightning,
  CheckCircle2
} from "lucide-react";

export default function SettingsPage() {
  const [apiUrl, setApiUrl] = useState("http://localhost:8000/api/v1");
  const [useMocks, setUseMocks] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div className="space-y-8 animate-fade-in max-w-2xl">
      {/* Heading */}
      <div>
        <h2 className="text-3xl font-bold font-heading text-slate-100 tracking-tight">System Settings</h2>
        <p className="text-slate-400 text-sm">Configure backend endpoints, database credentials, and AWS Solutions architecture nodes.</p>
      </div>

      <form onSubmit={handleSave} className="space-y-6 text-xs font-semibold text-slate-300">
        {/* Core Config */}
        <div className="glass-panel p-6 rounded-2xl space-y-4">
          <h3 className="text-sm font-bold font-heading text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
            <Server className="w-4 h-4 text-rose-500" />
            Backend Connection
          </h3>

          <div className="space-y-1">
            <label className="block text-slate-400 uppercase tracking-wider">FastAPI Service URL</label>
            <input 
              type="text" 
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="w-full px-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition font-semibold"
            />
          </div>
        </div>

        {/* AWS Solutions Architecture Config */}
        <div className="glass-panel p-6 rounded-2xl space-y-4">
          <h3 className="text-sm font-bold font-heading text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
            <CloudLightning className="w-4 h-4 text-accent" />
            AWS Architecture Integration
          </h3>

          {/* Toggle */}
          <div className="flex items-center justify-between p-3 bg-slate-900/30 border border-slate-800 rounded-xl">
            <div className="space-y-0.5">
              <h4 className="text-sm font-bold text-slate-200">Local Mocks Mode (Offline)</h4>
              <p className="text-[10px] text-slate-500 font-medium">Bypass actual Bedrock and DynamoDB instances, falling back to local mocks.</p>
            </div>
            <button 
              type="button"
              onClick={() => setUseMocks(!useMocks)}
              className="text-slate-400 hover:text-slate-200 transition"
            >
              {useMocks ? (
                <ToggleRight className="w-10 h-10 text-rose-500" />
              ) : (
                <ToggleLeft className="w-10 h-10 text-slate-500" />
              )}
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs font-semibold">
            <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800/80">
              <span className="text-slate-500 uppercase block mb-1">AWS Regions</span>
              <span className="text-sm text-slate-200">us-east-1</span>
            </div>
            <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800/80">
              <span className="text-slate-500 uppercase block mb-1">State Machine Status</span>
              <span className="text-sm text-rose-500">ASL Compliant</span>
            </div>
          </div>
        </div>

        {/* Database Config */}
        <div className="glass-panel p-6 rounded-2xl space-y-4">
          <h3 className="text-sm font-bold font-heading text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
            <Database className="w-4 h-4 text-accent-success" />
            Database Configuration
          </h3>

          <div className="grid grid-cols-2 gap-4 text-xs font-semibold">
            <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800/80">
              <span className="text-slate-500 uppercase block mb-1">Provider</span>
              <span className="text-sm text-slate-200">PostgreSQL</span>
            </div>
            <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800/80">
              <span className="text-slate-500 uppercase block mb-1">Connection Pool</span>
              <span className="text-sm text-slate-200">Active (10 connections)</span>
            </div>
          </div>
        </div>

        {/* Bottom Actions */}
        <div className="flex items-center gap-4">
          <button 
            type="submit"
            className="px-6 py-3 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl shadow-glass-primary transition duration-150 text-xs uppercase tracking-wider"
          >
            Save Changes
          </button>
          {saveSuccess && (
            <div className="flex items-center gap-1.5 text-xs text-accent-success font-semibold">
              <CheckCircle2 className="w-4 h-4" />
              Settings saved successfully!
            </div>
          )}
        </div>
      </form>
    </div>
  );
}
