"use client";

import { PanelLeftOpen, CalendarPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { ChatInput } from "@/components/chat/ChatInput";
import { ReservationModal } from "@/components/chat/ReservationModal";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { useChatStore } from "@/store/chatStore";
import { useUIStore } from "@/store/uiStore";
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

  // Show error toasts
  useEffect(() => {
    if (error) {
      toast.error("Error", { description: error });
      clearError();
    }
  }, [error, clearError]);

  return (
    <ErrorBoundary>
      <div className="flex flex-1 h-[calc(100vh-3.5rem)]">
        {/* Desktop sidebar */}
        <aside className="hidden md:flex w-64 border-r bg-card/50 backdrop-blur-sm flex-col">
          <ChatSidebar />
        </aside>

        {/* Mobile sidebar */}
        <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
          <SheetContent side="left" className="w-72 p-0">
            <ChatSidebar />
          </SheetContent>
        </Sheet>

        {/* Main chat area */}
        <div className="flex flex-1 flex-col min-w-0">
          {/* Chat header */}
          <div className="flex items-center gap-2 border-b px-3 py-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 md:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <PanelLeftOpen className="h-4 w-4" />
            </Button>
            <h2 className="text-sm font-medium flex-1">ParkSmart AI</h2>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              onClick={() => setReservationModalOpen(true)}
            >
              <CalendarPlus className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Book Parking</span>
            </Button>
          </div>

          {/* Messages */}
          <ChatWindow />

          {/* Input */}
          <ChatInput onSend={sendMessage} disabled={isLoading} />
        </div>
      </div>

      <ReservationModal />
    </ErrorBoundary>
  );
}
