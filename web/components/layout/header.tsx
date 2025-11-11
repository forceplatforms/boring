"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { ChevronRight, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

export function Header() {
  const pathname = usePathname();

  // Generate breadcrumbs from pathname
  const segments = pathname.split("/").filter(Boolean);
  const breadcrumbs = segments.map((segment, index) => ({
    label: segment.charAt(0).toUpperCase() + segment.slice(1),
    href: "/" + segments.slice(0, index + 1).join("/"),
    isLast: index === segments.length - 1,
  }));

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-6">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-sm">
        <Link
          href="/"
          className="text-muted-foreground transition-colors hover:text-foreground"
        >
          Home
        </Link>
        {breadcrumbs.map((crumb) => (
          <div key={crumb.href} className="flex items-center gap-2">
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
            {crumb.isLast ? (
              <span className="font-medium text-foreground">
                {crumb.label}
              </span>
            ) : (
              <Link
                href={crumb.href}
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                {crumb.label}
              </Link>
            )}
          </div>
        ))}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Search Bar */}
      <div className="relative w-64">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search..."
          className="h-9 pl-9 bg-background-secondary border-border/50"
        />
      </div>

      {/* User Menu Placeholder */}
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-medium text-primary-foreground">
          CG
        </div>
      </div>
    </header>
  );
}
