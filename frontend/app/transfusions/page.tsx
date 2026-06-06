"use client";

import { useEffect, useState } from "react";
import { useStore } from "@/store/useStore";
import { apiService } from "@/services/api";
import { 
  Activity, 
  Clock, 
  CheckCircle, 
  XCircle, 
  ChevronRight, 
  Send,
  AlertTriangle,
  UserCheck,
  Calendar,
  MessageSquare
} from "lucide-react";

export default function TransfusionsPage() {
  const { activeWorkflow, fetchWorkflowStatus, submitOutreachResponse, isLoading } = useStore();
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>("tx-mock-12345");
  const [workflowIds, setWorkflowIds] = useState<string[]>(["tx-mock-12345"]);

  useEffect(() => {
    // If we have an active workflow in Zustand store, add it to our tracking list
    if (activeWorkflow && !workflowIds.includes(activeWorkflow.workflow_id)) {
      setWorkflowIds(prev => [activeWorkflow.workflow_id, ...prev]);
      setSelectedWorkflowId(activeWorkflow.workflow_id);
    }
  }, [activeWorkflow, workflowIds]);

  useEffect(() => {
    if (!selectedWorkflowId) return;
    
    // Initial fetch
    fetchWorkflowStatus(selectedWorkflowId);
    
    // Poll every 3 seconds while the workflow is running
    const interval = setInterval(() => {
      const state = useStore.getState();
      const current = state.activeWorkflow;
      if (current && (current.status === "Completed" || current.status === "Failed")) {
        clearInterval(interval);
      } else {
        fetchWorkflowStatus(selectedWorkflowId);
      }
    }, 3000);
    
    return () => clearInterval(interval);
  }, [selectedWorkflowId, fetchWorkflowStatus]);

  const handleSimulateResponse = async (accept: boolean) => {
    if (!selectedWorkflowId) return;
    await submitOutreachResponse(selectedWorkflowId, accept);
  };

  // Steps in workflow timeline for visual gauge
  const workflowSteps = [
    { name: "Request Created", status: "Completed" },
    { name: "Find Donors", status: "Completed" },
    { name: "Rank Donors", status: "Completed" },
    { name: "Outreach Sent", status: "Pending" },
    { name: "Schedule Donation", status: "Pending" }
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold font-heading text-slate-100 tracking-tight">Active Care Bridges</h2>
        <p className="text-slate-400 text-sm">Trace the live state timelines of transfusion coordinates, outreach messages, and donation schedules.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Sidebar list */}
        <div className="lg:col-span-4 glass-panel p-5 rounded-2xl space-y-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-rose-500" />
            Active Workflow Sessions
          </h3>

          <div className="space-y-2">
            {workflowIds.map((id) => {
              const isActive = selectedWorkflowId === id;
              return (
                <button
                  key={id}
                  onClick={() => setSelectedWorkflowId(id)}
                  className={`w-full text-left p-3.5 rounded-xl border text-xs font-semibold flex items-center justify-between transition ${
                    isActive 
                      ? "bg-rose-600/10 text-rose-500 border-rose-500/30" 
                      : "bg-slate-900/40 text-slate-400 border-slate-800 hover:bg-slate-800/40"
                  }`}
                >
                  <div className="space-y-0.5">
                    <span className="block font-bold text-slate-200 uppercase">{id}</span>
                    <span className="text-[10px] text-slate-500 font-semibold uppercase">Care Bridge tracking</span>
                  </div>
                  <ChevronRight className="w-4 h-4" />
                </button>
              );
            })}
          </div>
        </div>

        {/* Timeline Tracking View */}
        {activeWorkflow ? (
          <div className="lg:col-span-8 glass-panel p-6 rounded-2xl space-y-6">
            <div className="flex items-start justify-between border-b border-slate-800/80 pb-4">
              <div>
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Workflow Dashboard</span>
                <h3 className="text-lg font-bold font-heading text-rose-500 uppercase">{activeWorkflow.workflow_id}</h3>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2.5 py-1 text-xs font-bold rounded-full ${
                  activeWorkflow.status === "Completed" 
                    ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" 
                    : activeWorkflow.status === "Failed" 
                    ? "bg-red-500/10 text-red-500 border border-red-500/20" 
                    : "bg-amber-500/10 text-amber-500 border border-amber-500/20 animate-pulse"
                }`}>
                  {activeWorkflow.status}
                </span>
              </div>
            </div>

            {/* Steps Progress Visualizer */}
            <div className="grid grid-cols-5 gap-2 text-center text-[10px] font-bold uppercase tracking-wider text-slate-500">
              {workflowSteps.map((step, idx) => {
                const workflowStep = activeWorkflow.current_step;
                let isPassed = false;
                
                if (workflowStep === "Schedule Donation") isPassed = true;
                else if (workflowStep === "Process Response" && idx < 4) isPassed = true;
                else if (workflowStep === "Outreach Sent" && idx < 4) isPassed = true;
                else if (workflowStep === "Rank Donors" && idx < 3) isPassed = true;
                else if (workflowStep === "Find Donors" && idx < 2) isPassed = true;
                else if (workflowStep === "Request Created" && idx < 1) isPassed = true;

                const isCurrent = workflowStep === step.name || (workflowStep === "Process Response" && step.name === "Outreach Sent");

                return (
                  <div key={idx} className="space-y-2">
                    <div className={`h-1.5 rounded-full ${
                      isPassed ? "bg-rose-600" : isCurrent ? "bg-rose-500 animate-pulse" : "bg-slate-800"
                    }`}></div>
                    <span className={isPassed || isCurrent ? "text-slate-300 font-semibold" : ""}>{step.name}</span>
                  </div>
                );
              })}
            </div>

            {/* Timeline details checklist */}
            <div className="space-y-4 pt-4 border-t border-slate-800/60">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Execution Timeline</h4>
              
              <div className="timeline-glow space-y-6 pl-1 select-none">
                {activeWorkflow.timeline.map((item: any, idx: number) => {
                  const isDone = item.status === "Success";
                  const isFail = item.status === "Failed" || item.status === "Declined";
                  return (
                    <div key={idx} className="relative z-10 flex items-start gap-4 animate-fade-in">
                      {/* Bullet icon */}
                      <span className={`flex items-center justify-center w-6 h-6 rounded-full border shrink-0 bg-slate-950 ${
                        isFail 
                          ? "border-red-500/40 text-red-500" 
                          : isDone 
                          ? "border-emerald-500/40 text-emerald-500" 
                          : "border-rose-500/40 text-rose-500 animate-pulse"
                      }`}>
                        {isFail ? <XCircle className="w-3.5 h-3.5" /> : isDone ? <CheckCircle className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
                      </span>
                      {/* Message body */}
                      <div className="p-3.5 bg-slate-900/40 border border-slate-800 rounded-2xl flex-1 text-xs">
                        <div className="flex items-center justify-between text-slate-400 font-semibold mb-1">
                          <span className="text-slate-200">{item.step}</span>
                          <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-slate-300 font-medium">{item.message}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Simulator Actions panel */}
            {activeWorkflow.status === "Outreach Sent" && (
              <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl space-y-4 animate-fade-in">
                <div className="flex items-center gap-2 text-xs text-rose-500 font-bold uppercase tracking-wider">
                  <UserCheck className="w-4 h-4" />
                  Donor Response Simulator
                </div>
                <p className="text-xs text-slate-300">
                  Donor receives a WhatsApp notification detailing the transfusion match. Simulate donor response below to advance uvicorn's state machine.
                </p>
                <div className="flex gap-4">
                  <button
                    onClick={() => handleSimulateResponse(true)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-sm text-xs transition duration-150"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Simulate Accept
                  </button>
                  <button
                    onClick={() => handleSimulateResponse(false)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl shadow-sm text-xs transition duration-150"
                  >
                    <XCircle className="w-4 h-4" />
                    Simulate Decline
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="lg:col-span-8 text-center py-20 text-slate-500 border border-dashed border-slate-800 rounded-2xl">
            No active workflows tracked. Go to matching page to trigger one!
          </div>
        )}
      </div>
    </div>
  );
}
