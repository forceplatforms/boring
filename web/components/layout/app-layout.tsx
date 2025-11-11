import { Sidebar } from "./sidebar";
import { Header } from "./header";

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="relative min-h-screen bg-background">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content area */}
      <div className="pl-64">
        {/* Header */}
        <Header />

        {/* Page content */}
        <main className="min-h-[calc(100vh-4rem)] p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
