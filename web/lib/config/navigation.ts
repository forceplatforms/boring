import {
  FileText,
  Shield,
  AlertTriangle,
  CheckCircle2,
  LayoutDashboard,
  Search,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  description: string;
  badge?: number;
}

export const navigation: NavItem[] = [
  {
    title: "Documents",
    href: "/documents",
    icon: FileText,
    description: "Manage and ingest compliance documents",
  },
  {
    title: "Search",
    href: "/search",
    icon: Search,
    description: "Search documents with AI-powered semantic search",
  },
  {
    title: "Frameworks",
    href: "/frameworks",
    icon: Shield,
    description: "Configure compliance frameworks and requirements",
  },
  {
    title: "Compliance",
    href: "/compliance",
    icon: CheckCircle2,
    description: "Run and monitor compliance scans",
  },
  {
    title: "Violations",
    href: "/violations",
    icon: AlertTriangle,
    description: "Review and remediate compliance violations",
  },
];

export const getNavigationWithBadges = (
  violationCount?: number
): NavItem[] => {
  return navigation.map((item) => {
    if (item.href === "/violations" && violationCount) {
      return { ...item, badge: violationCount };
    }
    return item;
  });
};
