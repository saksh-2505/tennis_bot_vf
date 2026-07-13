"use client";

import React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard, Radio, Search, Server, Link as LinkIcon,
  Compass, BookOpen, Database, ShieldCheck, CheckCircle,
  FileCheck, Eye, GitBranch, AlertTriangle, Wrench,
  FileText, TrendingUp, Clock, ScrollText,
} from "lucide-react";

interface NavSection {
  title: string;
  items: { href: string; label: string; icon: React.ReactNode }[];
}

const sections: NavSection[] = [
  {
    title: "Monitor",
    items: [
      { href: "/", label: "Overview", icon: <LayoutDashboard className="h-4 w-4" /> },
      { href: "/matches/live", label: "Live Matches", icon: <Radio className="h-4 w-4" /> },
      { href: "/matches", label: "Match Explorer", icon: <Search className="h-4 w-4" /> },
    ],
  },
  {
    title: "Data Pipeline",
    items: [
      { href: "/collectors", label: "Collectors", icon: <Server className="h-4 w-4" /> },
      { href: "/matching", label: "Market Matching", icon: <LinkIcon className="h-4 w-4" /> },
      { href: "/discovery", label: "Discovery", icon: <Compass className="h-4 w-4" /> },
      { href: "/registry", label: "Registry", icon: <BookOpen className="h-4 w-4" /> },
    ],
  },
  {
    title: "Quality & Repair",
    items: [
      { href: "/quality", label: "Quality", icon: <ShieldCheck className="h-4 w-4" /> },
      { href: "/validation", label: "Validation", icon: <CheckCircle className="h-4 w-4" /> },
      { href: "/verification", label: "Verification", icon: <FileCheck className="h-4 w-4" /> },
      { href: "/observability", label: "Observability", icon: <Eye className="h-4 w-4" /> },
    ],
  },
  {
    title: "Operations",
    items: [
      { href: "/pipeline", label: "Pipeline", icon: <GitBranch className="h-4 w-4" /> },
      { href: "/incidents", label: "Incidents", icon: <AlertTriangle className="h-4 w-4" /> },
      { href: "/repair", label: "Repair", icon: <Wrench className="h-4 w-4" /> },
      { href: "/reports", label: "Reports", icon: <FileText className="h-4 w-4" /> },
    ],
  },
  {
    title: "Tools",
    items: [
      { href: "/analytics", label: "Analytics", icon: <TrendingUp className="h-4 w-4" /> },
      { href: "/search", label: "Search", icon: <Search className="h-4 w-4" /> },
      { href: "/timeline", label: "Timeline", icon: <Clock className="h-4 w-4" /> },
      { href: "/logs", label: "Logs", icon: <ScrollText className="h-4 w-4" /> },
      { href: "/database", label: "Database", icon: <Database className="h-4 w-4" /> },
    ],
  },
];

interface SidebarProps {
  pathname: string;
}

export function Sidebar({ pathname }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-[280px] border-r border-slate-800 bg-slate-950 flex flex-col">
      <div className="flex h-14 items-center border-b border-slate-800 px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold text-emerald-400">
          <Database className="h-5 w-5" />
          <span>Dev Console</span>
        </Link>
      </div>
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        {sections.map((section) => (
          <div key={section.title} className="mb-4">
            <h4 className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              {section.title}
            </h4>
            {section.items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  pathname === item.href
                    ? "bg-emerald-600/10 text-emerald-400"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                )}
              >
                {item.icon}
                {item.label}
              </Link>
            ))}
          </div>
        ))}
      </nav>
      <div className="border-t border-slate-800 px-4 py-3">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <div className="h-2 w-2 rounded-full bg-emerald-500" />
          Sports Trading Platform v4.0
        </div>
      </div>
    </aside>
  );
}
