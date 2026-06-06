"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard");
  }, [router]);

  return (
    <div className="flex h-[70vh] items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-rose-600 border-t-transparent"></div>
        <p className="text-sm font-medium text-slate-400">Loading Blood Warriors Command Center...</p>
      </div>
    </div>
  );
}
