"use client";

import { useEffect, useRef, useState } from "react";
import { useStore } from "@/store/useStore";
import { 
  MessageSquare, 
  Send, 
  Sparkles, 
  Trash2, 
  User, 
  Compass,
  FileText
} from "lucide-react";

const SUGGESTIONS = [
  "What is Thalassemia?",
  "How can it be prevented?",
  "What is carrier screening?",
  "Who is eligible to donate blood?"
];

export default function AwarenessPage() {
  const { chatHistory, sendMessage, clearChat, isLoading } = useStore();
  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputText.trim() || isLoading) return;
    const txt = inputText;
    setInputText("");
    await sendMessage(txt);
  };

  const handleSuggestionClick = async (suggestion: string) => {
    if (isLoading) return;
    await sendMessage(suggestion);
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl mx-auto">
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-3xl font-bold font-heading text-slate-100 tracking-tight flex items-center gap-2">
            <Sparkles className="w-8 h-8 text-rose-500 animate-pulse" />
            Awareness Co-Pilot
          </h2>
          <p className="text-slate-400 text-sm">Consult our AI Assistant about Thalassemia genetics, screening registries, and prevention protocols.</p>
        </div>
        <button
          onClick={clearChat}
          className="p-2 bg-slate-800/40 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 rounded-xl transition duration-150 text-xs font-semibold flex items-center gap-1.5"
          title="Clear Conversation"
        >
          <Trash2 className="w-4 h-4" />
          Clear
        </button>
      </div>

      {/* Main chat box */}
      <div className="glass-panel rounded-2xl flex flex-col h-[55vh] overflow-hidden">
        {/* Messages container */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {chatHistory.map((msg) => {
            const isUser = msg.sender === "user";
            return (
              <div 
                key={msg.id}
                className={`flex gap-3 max-w-[80%] ${isUser ? "ml-auto flex-row-reverse" : "mr-auto"}`}
              >
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full border flex items-center justify-center shrink-0 text-xs font-semibold ${
                  isUser 
                    ? "bg-slate-800 border-slate-700 text-slate-300" 
                    : "bg-rose-600/10 border-rose-500/20 text-rose-500"
                }`}>
                  {isUser ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
                </div>

                {/* Msg text bubble */}
                <div className="space-y-2">
                  <div className={`p-4 rounded-2xl text-xs leading-relaxed ${
                    isUser 
                      ? "bg-rose-600 text-white rounded-tr-none" 
                      : "bg-slate-900 border border-slate-800/80 text-slate-200 rounded-tl-none"
                  }`}>
                    {msg.text}
                  </div>

                  {/* Sources display */}
                  {!isUser && msg.sources && msg.sources.length > 0 && (
                    <div className="flex items-center gap-1 text-[9px] font-bold text-slate-500 uppercase tracking-wider pl-2">
                      <FileText className="w-3.5 h-3.5 text-slate-500" />
                      <span>RAG Sources: {msg.sources.join(", ")}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          
          {isLoading && (
            <div className="flex gap-3 max-w-[80%] mr-auto items-center">
              <div className="w-8 h-8 rounded-full bg-rose-600/10 border border-rose-500/20 flex items-center justify-center text-rose-500">
                <Sparkles className="w-4 h-4 animate-spin" />
              </div>
              <div className="p-4 bg-slate-900 border border-slate-800/80 rounded-2xl rounded-tl-none text-xs text-slate-500 font-semibold italic animate-pulse">
                Consulting Thalassemia knowledge registers...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggestion Chips */}
        {chatHistory.length === 1 && !isLoading && (
          <div className="px-6 pb-2 space-y-2">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
              <Compass className="w-4 h-4" />
              Suggested Questions
            </h4>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSuggestionClick(s)}
                  className="px-3.5 py-2 text-xs font-semibold bg-slate-900 border border-slate-800 hover:border-rose-500/30 text-slate-300 hover:text-slate-100 rounded-xl transition duration-150"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Form Input */}
        <form onSubmit={handleSend} className="p-4 border-t border-slate-800/60 bg-slate-950/20 flex gap-3">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Ask anything about thalassemia screening, genetic compatibility, pre-marital risks..."
            className="flex-1 px-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-rose-600 transition text-xs font-semibold"
            disabled={isLoading}
          />
          <button
            type="submit"
            className="p-3 bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow-glass-primary transition duration-150 shrink-0 flex items-center justify-center"
            disabled={isLoading || !inputText.trim()}
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
