"use client";

import { useEffect, useState } from "react";
import { useStore } from "@/store/useStore";
import { 
  Users, 
  Droplets, 
  Clock, 
  ShieldCheck, 
  AlertTriangle, 
  Sparkles,
  ArrowUpRight,
  TrendingUp,
  Activity
} from "lucide-react";

// Dynamically import Recharts to avoid SSR hydration issues
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend
} from "recharts";

const COLORS = ["#e11d48", "#f43f5e", "#fda4af", "#3b82f6", "#10b981", "#f59e0b"];

export default function Dashboard() {
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
          <p className="text-sm text-slate-400 font-medium">Fetching dashboard metrics...</p>
        </div>
      </div>
    );
  }

  const { summary, donation_trends, blood_group_distribution, retention_trends, forecasts } = dashboard;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Page Heading */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold font-heading text-slate-100 tracking-tight">Command Center</h2>
          <p className="text-slate-400 text-sm">Real-time coordinates and predictive metrics for Thalassemia care bridges.</p>
        </div>
        <button 
          onClick={fetchDashboard}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 hover:text-slate-100 hover:bg-slate-700 rounded-xl transition duration-200 text-sm font-semibold"
        >
          <Clock className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-5">
        {/* Total Patients */}
        <div className="glass-card p-5 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Patients</span>
            <Users className="w-5 h-5 text-accent" />
          </div>
          <div className="mt-4">
            <h3 className="text-2xl font-bold font-heading text-slate-100">{summary.total_patients}</h3>
            <p className="text-[10px] text-slate-400 mt-1 font-semibold flex items-center gap-1">
              <span className="text-accent-success flex items-center">↑ 4%</span> vs last month
            </p>
          </div>
        </div>

        {/* Total Donors */}
        <div className="glass-card p-5 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Donors</span>
            <Droplets className="w-5 h-5 text-rose-500" />
          </div>
          <div className="mt-4">
            <h3 className="text-2xl font-bold font-heading text-rose-500">{summary.total_donors}</h3>
            <p className="text-[10px] text-slate-400 mt-1 font-semibold flex items-center gap-1">
              <span className="text-accent-success flex items-center">↑ 12</span> new registration
            </p>
          </div>
        </div>

        {/* Active Donors */}
        <div className="glass-card p-5 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Donors</span>
            <ShieldCheck className="w-5 h-5 text-accent-success" />
          </div>
          <div className="mt-4">
            <h3 className="text-2xl font-bold font-heading text-accent-success">{summary.active_donors}</h3>
            <p className="text-[10px] text-slate-400 mt-1 font-semibold">
              Currently eligible
            </p>
          </div>
        </div>

        {/* High Risk Patients */}
        <div className="glass-card p-5 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">High Risk</span>
            <AlertTriangle className="w-5 h-5 text-accent-danger animate-pulse" />
          </div>
          <div className="mt-4">
            <h3 className="text-2xl font-bold font-heading text-accent-danger">{summary.high_risk_patients}</h3>
            <p className="text-[10px] text-slate-400 mt-1 font-semibold">
              Bridge shortage risk
            </p>
          </div>
        </div>

        {/* Upcoming Transfusions */}
        <div className="glass-card p-5 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Upcoming TX</span>
            <Clock className="w-5 h-5 text-accent-warning" />
          </div>
          <div className="mt-4">
            <h3 className="text-2xl font-bold font-heading text-accent-warning">{summary.upcoming_transfusions}</h3>
            <p className="text-[10px] text-slate-400 mt-1 font-semibold">
              Next 14 days
            </p>
          </div>
        </div>

        {/* Match Success Rate */}
        <div className="glass-card p-5 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">AI Success</span>
            <Sparkles className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="mt-4">
            <h3 className="text-2xl font-bold font-heading text-indigo-400">{summary.ai_match_success_rate}%</h3>
            <p className="text-[10px] text-slate-400 mt-1 font-semibold">
              Predictive matches
            </p>
          </div>
        </div>
      </div>

      {/* Main Row Charts & Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Donation & Supply Trends Chart */}
        <div className="glass-panel p-6 rounded-2xl lg:col-span-2">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-bold font-heading text-slate-100">Donation & Deficit Trends</h3>
              <p className="text-xs text-slate-400">Monthly blood supply levels vs transfusion deficit requests.</p>
            </div>
            <span className="flex items-center gap-1 text-xs text-rose-500 font-semibold bg-rose-500/10 px-2 py-1 rounded-lg border border-rose-500/20">
              <TrendingUp className="w-3.5 h-3.5" />
              Rising Supply
            </span>
          </div>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={donation_trends}>
                <defs>
                  <linearGradient id="colorDonations" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#e11d48" stopOpacity={0.25}/>
                    <stop offset="95%" stopColor="#e11d48" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorShortages" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.15}/>
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", borderRadius: "12px", color: "#f8fafc" }} />
                <Area type="monotone" dataKey="donations" stroke="#e11d48" strokeWidth={2} fillOpacity={1} fill="url(#colorDonations)" name="Supply Units" />
                <Area type="monotone" dataKey="shortages" stroke="#ef4444" strokeWidth={1} strokeDasharray="5 5" fillOpacity={1} fill="url(#colorShortages)" name="Unmatched Requests" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Predictions & Insights Panel */}
        <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-rose-500" />
              <h3 className="text-lg font-bold font-heading text-slate-100">AI Predictive Insights</h3>
            </div>
            <div className="space-y-4">
              {/* Forecast Alert */}
              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-800 space-y-1">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-accent-warning">Supply-Demand Deficit Warning</h4>
                <p className="text-sm text-slate-200">
                  Anticipated shortage of <span className="font-semibold text-rose-500">O Positive</span> units next month: {forecasts.demand_next_month - forecasts.supply_next_month} units needed.
                </p>
                <div className="text-[10px] text-slate-500 font-semibold pt-1">
                  Risk Category: {forecasts.shortage_risk}
                </div>
              </div>

              {/* Recommended Action */}
              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-800 space-y-1">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-accent-success">Target Screening Drive</h4>
                <p className="text-sm text-slate-200">
                  Highly recommend launching a collegiate/corporate HPLC screening drive at <span className="font-semibold text-slate-100">{forecasts.recommended_screening_location}</span> to register 40+ O-positive donors.
                </p>
              </div>

              {/* Action recommendation links */}
              <div className="p-4 rounded-xl bg-rose-500/5 border border-rose-500/10 space-y-2">
                <h4 className="text-xs font-semibold text-rose-500 uppercase tracking-wider">Pending Coordinator Actions</h4>
                <ul className="text-xs text-slate-300 space-y-2.5">
                  <li className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-600 mt-1.5"></span>
                    <span>Outreach logs indicate 3 emergency donor escalations active.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-600 mt-1.5"></span>
                    <span>14 high-churn regular donors require retention token messaging.</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span>LLM: Bedrock Ready</span>
            <span className="flex items-center gap-1 text-rose-500 hover:text-rose-400 cursor-pointer">
              View Analytics <ArrowUpRight className="w-3.5 h-3.5" />
            </span>
          </div>
        </div>
      </div>

      {/* Row 2: Distributions and Retention */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Retention trends */}
        <div className="glass-panel p-6 rounded-2xl lg:col-span-2">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-bold font-heading text-slate-100">Donor Retention & Activity</h3>
              <p className="text-xs text-slate-400">Monthly progression of active donor retention rates and WhatsApp reply ratios.</p>
            </div>
          </div>
          <div className="h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={retention_trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f8fafc" }} />
                <Area type="monotone" dataKey="retention_rate" stroke="#10b981" strokeWidth={2} fill="none" name="Retention Rate (%)" />
                <Area type="monotone" dataKey="active_ratio" stroke="#3b82f6" strokeWidth={1.5} fill="none" name="WhatsApp Reply Ratio (%)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Blood Group Distribution */}
        <div className="glass-panel p-6 rounded-2xl">
          <h3 className="text-lg font-bold font-heading text-slate-100 mb-6">Blood Register Profile</h3>
          <div className="h-[200px] relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={blood_group_distribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="count"
                  nameKey="blood_group"
                >
                  {blood_group_distribution.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f8fafc" }} />
              </PieChart>
            </ResponsiveContainer>
            {/* Center Label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none mt-2">
              <span className="text-2xl font-bold font-heading text-slate-100">{summary.total_donors}</span>
              <span className="text-[9px] uppercase font-bold text-slate-500 tracking-wider">Donors</span>
            </div>
          </div>

          {/* Custom Legend */}
          <div className="grid grid-cols-3 gap-2 mt-4 text-[10px] font-semibold text-slate-400">
            {blood_group_distribution.slice(0, 6).map((item: any, index: number) => (
              <div key={item.blood_group} className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }}></span>
                <span className="truncate">{item.blood_group} ({item.count})</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
