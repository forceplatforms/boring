import { AppLayout } from "@/components/layout/app-layout";

export default function SearchLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppLayout>{children}</AppLayout>;
}
