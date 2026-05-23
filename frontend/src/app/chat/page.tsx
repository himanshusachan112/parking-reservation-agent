"use client";

import { PanelLeftOpen, CalendarPlus, Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { ChatInput } from "@/components/chat/ChatInput";
import { ReservationModal } from "@/components/chat/ReservationModal";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { useChatStore } from "@/store/chatStore";
import { useUIStore } from "@/store/uiStore";
import { useBackendReady } from "@/hooks/useBackendReady";
import { toast } from "sonner";
import { useEffect } from "react";

export default function ChatPage() {
  const sendMessage = useChatStore((s) => s.sendMessage);
  const isLoading = useChatStore((s) => s.isLoading);
  const error = useChatStore((s) => s.error);
  const clearError = useChatStore((s) => s.clearError);
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const setReservationModalOpen = useUIStore(
    (s) => s.setReservationModalOpen
  );

  const { ready: backendReady, message: backendMessage } = useBackendReady();

  // Show error toasts
  useEffect(() => {
    if (error) {
      toast.error("Error", { description: error });
      clearError();
    }
  }, [error, clearError]);

  return (
    <ErrorBoundary>
      <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
        {/* Desktop sidebar — fixed, independent scroll */}
        <aside className="hidden md:flex w-72 shrink-0 border-r bg-card/60 backdrop-blur-xl flex-col h-full overflow-hidden">
          <ChatSidebar />
        </aside>

        {/* Mobile sidebar drawer */}
        <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
          <SheetContent side="left" className="w-72 p-0">
            <ChatSidebar />
          </SheetContent>
        </Sheet>

        {/* Main chat area — isolated scroll */}
        <div className="flex flex-1 flex-col min-w-0 h-full overflow-hidden">
          {/* Chat header */}
          <div className="flex items-center gap-2 border-b bg-background/80 backdrop-blur-xl px-4 py-2.5 shrink-0 z-10">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 md:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <PanelLeftOpen className="h-4 w-4" />
            </Button>
            <div className="flex items-center gap-2 flex-1">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-600 shadow-sm">
                <Sparkles className="h-3.5 w-3.5 text-white" />
              </div>
              <div>
                <h2 className="text-sm font-semibold leading-none">ParkSmart AI</h2>
                <p className="text-[10px] text-muted-foreground leading-none mt-0.5">Parking Assistant</p>
              </div>
            </div>
            {/* Backend readiness indicator */}
            {!backendReady && (
              <div className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-lg px-2.5 py-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                <span className="hidden sm:inline">Warming up…</span>
              </div>
            )}
            {backendReady && (
              <div className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="hidden sm:inline">Ready</span>
              </div>
            )}
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs rounded-lg"
              onClick={() => setReservationModalOpen(true)}
            >
              <CalendarPlus className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Book Parking</span>
            </Button>
          </div>

          {/* Warming-up banner — shown while pipeline is loading */}
          {!backendReady && (
            <div className="shrink-0 bg-amber-50 dark:bg-amber-950/30 border-b border-amber-200 dark:border-amber-800 px-4 py-2.5 flex items-center gap-2.5">
              <Loader2 className="h-4 w-4 text-amber-600 dark:text-amber-400 animate-spin shrink-0" />
              <div>
                <p className="text-xs font-medium text-amber-800 dark:text-amber-300">
                  AI is warming up
                </p>
                <p className="text-[11px] text-amber-700 dark:text-amber-400">
                  {backendMessage} — your first message will be answered once ready.
                </p>
              </div>
            </div>
          )}

          {/* Messages — scrollable */}
          <ChatWindow />

          {/* Input — sticky bottom */}
          <ChatInput onSend={sendMessage} disabled={isLoading || !backendReady} />
        </div>
      </div>

      <ReservationModal />
    </ErrorBoundary>
  );
}
