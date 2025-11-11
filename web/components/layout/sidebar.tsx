"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import { navigation } from "@/lib/config/navigation";
import { Badge } from "@/components/ui/badge";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-border bg-background-secondary">
      {/* Logo/Brand */}
      <div className="flex h-16 items-center gap-3 border-b border-border px-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
          <Shield className="h-6 w-6 text-primary-foreground" />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold leading-none text-foreground">
            ComplianceGuard
          </span>
          <span className="text-xs text-muted-foreground">AI Platform</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 p-4">
        {navigation.map((item) => {
          const isActive = pathname.startsWith(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                "hover:bg-accent/50",
                isActive
                  ? "bg-accent text-accent-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {/* Active indicator */}
              {isActive && (
                <div className="absolute left-0 top-1/2 h-8 w-1 -translate-y-1/2 rounded-r-full bg-primary" />
              )}

              <Icon
                className={cn(
                  "h-5 w-5 shrink-0 transition-colors",
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground group-hover:text-foreground"
                )}
              />

              <span className="flex-1">{item.title}</span>

              {item.badge !== undefined && item.badge > 0 && (
                <Badge
                  variant="destructive"
                  className="h-5 min-w-5 px-1.5 text-xs"
                >
                  {item.badge > 99 ? "99+" : item.badge}
                </Badge>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Bottom section - Status */}
      <div className="absolute bottom-0 left-0 right-0 border-t border-border bg-background-secondary p-4">
        <div className="flex items-center gap-2 rounded-lg bg-background px-3 py-2">
          <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs text-muted-foreground">
            API Connected
          </span>
        </div>
      </div>
    </aside>
  );
}
