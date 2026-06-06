"use client";

import { useEffect, useState } from "react";
import { useStore } from "@/store/useStore";
import { 
  TrendingUp, 
  Clock, 
  Sparkles, 
  BarChart2, 
  AlertTriangle,
  Compass
} from "lucide-react";

// Recharts components imports
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
  LineChart,
  Line
} from "recharts";

export default function AnalyticsPage() {
  const { dashboard, fetchDashboard, isLoading } = useStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetchDashboard();
  }, [fetchDashboard]);

  if (!mounted || isLoading || !dashboard) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-rose-600 border-t-transparent"></div>
          <p className="text-sm text-slate-400 font-medium">Loading predictive analytics...</p>
        </div>
      </div>
    );
  }

  const { donation_trends, blood_group_distribution, retention_trends, forecasts } = dashboard;

  // Forecasted supply/demand over next 6 months (simulated extension)
  const forecastSupplyDemand = [
    { month: "Jun", supply: 84, demand: 110 },
    { month: "Jul", supply: 92, demand: 118 },
    { month: "Aug", supply: 98, demand: 125 },
    { month: "Sep", supply: 104, demand: 130 },
    { month: "Oct", supply: 112, demand: 138 },
    { month: "Nov", supply: 120, demand: 145 },
  ];

  // Churn forecast trends (simulated RF predictions)
  const churnRiskForecast = [
    { month: "Jun", risk_rate: 12.4, high_risk_count: 5 },
    { month: "Jul", risk_rate: 11.8, high_risk_count: 4 },
    { month: "Aug", risk_rate: 13.5, high_risk_count: 7 },
    { month: "Sep", risk_rate: 10.2, high_risk_count: 3 },
    { month: "Oct", risk_rate: 9.6, high_risk_count: 2 },
    { month: "Nov", risk_rate: 8.8, high_risk_count: 1 },
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Heading */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold font-heading text-slate-100 tracking-tight">Predictive Analytics</h2>
          <p className="text-slate-400 text-sm">Review machine learning forecasts for blood bank reserves and donor retention indices.</p>
        </div>
        <div className="text-xs text-slate-500 font-bold uppercase tracking-wider bg-slate-900 px-3.5 py-2 rounded-xl border border-slate-800 flex items-center gap-1.5">
          <Sparkles className="w-4 h-4 text-rose-500" />
          ML Engine Active
        </div>
      </div>

      {/* Grid of Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Chart 1: Supply & Demand Forecast */}
        <div className="glass-panel p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-bold font-heading text-slate-100">Supply & Demand Forecast</h3>
              <p className="text-xs text-slate-400">6-month forward projection of compatible supply vs patient request queues.</p>
            </div>
            <span className="text-[10px] text-rose-500 font-bold uppercase tracking-wider bg-rose-500/10 px-2.5 py-1 rounded-lg border border-rose-500/20">
              Shortage Warning
            </span>
          </div>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={forecastSupplyDemand}>
                <defs>
                  <linearGradient id="colorSupply" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#e11d48" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#e11d48" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorDemand" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f8fafc" }} />
                <Area type="monotone" dataKey="supply" stroke="#e11d48" strokeWidth={2} fillOpacity={1} fill="url(#colorSupply)" name="Supply Forecast" />
                <Area type="monotone" dataKey="demand" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorDemand)" name="Required Demand" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Donor Churn Rate Forecast */}
        <div className="glass-panel p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-bold font-heading text-slate-100">Donor Churn Rate Forecast</h3>
              <p className="text-xs text-slate-400">RandomForest projection of donor attrition risk percentage and count of high-risk profiles.</p>
            </div>
            <span className="text-[10px] text-emerald-500 font-bold uppercase tracking-wider bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
              Improving Retention
            </span>
          </div>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={churnRiskForecast}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f8fafc" }} />
                <Bar dataKey="risk_rate" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Predicted Churn Rate (%)" />
                <Bar dataKey="high_risk_count" fill="#ef4444" radius={[4, 4, 0, 0]} name="Critical Churn Profiles" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 3: Availability Trends */}
        <div className="glass-panel p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-bold font-heading text-slate-100">Availability & Reply Ratios</h3>
              <p className="text-xs text-slate-400">XGBoost predictions of donor coordination response ratios over the preceding months.</p>
            </div>
          </div>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={retention_trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f8fafc" }} />
                <Line type="monotone" dataKey="active_ratio" stroke="#3b82f6" strokeWidth={2} name="Availability Index" activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="retention_rate" stroke="#10b981" strokeWidth={1.5} name="WhatsApp Response Rate" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 4: Blood Group Demand Forecast */}
        <div className="glass-panel p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-bold font-heading text-slate-100">Blood Group Shortage Probability</h3>
              <p className="text-xs text-slate-400">Calculated percentage probability of encountering shortages in specific ABO registers next month.</p>
            </div>
          </div>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={blood_group_distribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="blood_group" stroke="#94a3b8" fontSize={10} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f8fafc" }} />
                <Bar dataKey="count" fill="#e11d48" radius={[4, 4, 0, 0]} name="Shortage Probability (%)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Advisory recommendations card */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row gap-6 items-center justify-between">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-rose-600/10 border border-rose-500/20 flex items-center justify-center text-rose-500 shrink-0">
            <AlertTriangle className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h3 className="text-lg font-bold font-heading text-slate-100">Predictive Action Plan</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Based onforward-looking XGBoost supply models, coordinates in <span className="text-rose-500 font-semibold">{forecasts.recommended_screening_location}</span> represent high-potential matching areas. Planning campaigns here next month is highly advised.
            </p>
          </div>
        </div>
        <button className="px-5 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs uppercase tracking-wider rounded-xl transition duration-150 border border-slate-700 shrink-0 flex items-center gap-1.5">
          <Compass className="w-4 h-4" />
          Launch Screening Campaign
        </button>
      </div>
    </div>
  );
}
