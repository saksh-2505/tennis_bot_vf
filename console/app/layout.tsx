"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { Sidebar } from "@/components/layout/Sidebar";
import "@/app/globals.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchInterval: 15_000,
      retry: 1,
    },
  },
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <html lang="en">
      <head>
        <title>Sports Trading Platform — Dev Console</title>
        <meta name="description" content="Developer Console for Sports Trading Platform" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="bg-slate-950 text-slate-100 antialiased">
        <QueryClientProvider client={queryClient}>
          <div className="flex min-h-screen">
            <Sidebar pathname={pathname} />
            <main className="ml-[280px] flex-1 p-6">
              <div className="mb-6 flex items-center gap-4 rounded-lg border border-slate-800 bg-slate-900 px-4 py-2 text-sm">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-emerald-500" />
                  <span className="text-slate-400">DB:</span>
                  <span className="font-medium text-emerald-400">Connected</span>
                </div>
                <div className="text-slate-600">|</div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Live Matches:</span>
                  <span className="font-medium text-slate-200">—</span>
                </div>
                <div className="text-slate-600">|</div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Last Refresh:</span>
                  <span className="font-medium text-slate-200">—</span>
                </div>
              </div>
              {children}
            </main>
          </div>
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: "rgb(15, 23, 42)",
                color: "rgb(226, 232, 240)",
                border: "1px solid rgb(51, 65, 85)",
                fontSize: "13px",
              },
            }}
          />
        </QueryClientProvider>
      </body>
    </html>
  );
}
