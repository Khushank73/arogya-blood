"use client";

import { useEffect, useState } from "react";
import { useStore } from "@/store/useStore";

export default function LastSync() {
  const [mounted, setMounted] = useState(false);
  const [syncing, setSyncing] = useState(false);
  
  const lastSyncTime = useStore((state) => state.lastSyncTime);
  const fetchPatients = useStore((state) => state.fetchPatients);
  const fetchDonors = useStore((state) => state.fetchDonors);
  const fetchDashboard = useStore((state) => state.fetchDashboard);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleManualSync = async () => {
    setSyncing(true);
    try {
      await Promise.all([
        fetchPatients(),
        fetchDonors(),
        fetchDashboard()
      ]);
    } catch (err) {
      console.error("Manual sync failed:", err);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="flex items-center gap-2 select-none">
      <span className="text-xs text-slate-500 font-medium">
        Last Sync: {mounted ? (lastSyncTime || new Date().toLocaleTimeString()) : "Loading..."}
      </span>
      {mounted && (
        <button
          onClick={handleManualSync}
          disabled={syncing}
          className="p-1 rounded hover:bg-slate-800/80 text-slate-500 hover:text-rose-500 transition-colors duration-150 flex items-center justify-center disabled:opacity-50"
          title="Sync all registers now"
        >
          <svg
            className={`w-3.5 h-3.5 ${syncing ? "animate-spin text-rose-500" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M21 8h-5V3"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
