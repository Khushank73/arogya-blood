"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Users, 
  Droplets, 
  Shuffle, 
  Activity, 
  MessageSquare, 
  TrendingUp, 
  Settings,
  ShieldAlert,
  Network
} from "lucide-react";

const navItems = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Patients", href: "/patients", icon: Users },
  { name: "Donors", href: "/donors", icon: Droplets },
  { name: "Smart Matching", href: "/matching", icon: Shuffle },
  { name: "Care Bridges", href: "/bridges", icon: Network },
  { name: "Transfusions", href: "/transfusions", icon: Activity },
  { name: "Analytics", href: "/analytics", icon: TrendingUp },
  { name: "Settings", href: "/settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-20 flex w-64 flex-col bg-slate-900 border-r border-slate-800 text-slate-200">
      {/* Brand Logo */}
      <div className="flex h-16 items-center px-6 border-b border-slate-800 bg-slate-950 gap-2">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-rose-600 shadow-glass-primary">
          <Droplets className="w-5 h-5 text-white animate-pulse" />
        </div>
        <div>
          <h1 className="text-lg font-bold font-heading text-rose-500 tracking-tight leading-none">Blood Warriors</h1>
          <span className="text-[10px] text-slate-500 font-semibold tracking-wider uppercase">AI platform</span>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 space-y-1 px-4 py-6">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                isActive 
                  ? "bg-rose-600/10 text-rose-500 shadow-sm border-l-4 border-rose-600" 
                  : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
              }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? "text-rose-500" : "text-slate-400"}`} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/50">
        <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/40 border border-slate-800">
          <ShieldAlert className="w-5 h-5 text-rose-500" />
          <div>
            <h4 className="text-xs font-semibold text-slate-300">Coordinators Hub</h4>
            <span className="text-[10px] text-slate-500 font-medium">Secured Node</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
