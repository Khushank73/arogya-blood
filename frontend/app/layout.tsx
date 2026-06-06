import "./globals.css";
import Sidebar from "@/components/sidebar";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Blood Warriors AI | Care Coordination & Thalassemia Support",
  description: "AI-powered blood support and Thalassemia care platform automating donor engagement, availability predictions, and transfusion coordination.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="bg-background text-slate-200">
        <div className="flex min-h-screen">
          {/* Sidebar Navigation */}
          <Sidebar />

          {/* Main Layout Area */}
          <main className="flex-1 pl-64 min-h-screen">
            {/* Topbar Info Header */}
            <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-900/40 px-8 backdrop-blur-md">
              <div className="flex items-center gap-4">
                <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-500 border border-rose-500/20">
                  Node-01 Active
                </span>
                <span className="text-xs text-slate-500 font-medium">
                  Last Sync: {new Date().toLocaleDateString()}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-300">
                  BW
                </div>
                <span className="text-sm font-medium text-slate-300">Hyderabad Admin</span>
              </div>
            </header>

            {/* Render Child Pages */}
            <div className="p-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
