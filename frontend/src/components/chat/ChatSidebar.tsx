"use client";

import { Plus, MessageSquare, Trash2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/store/chatStore";
import { useUIStore } from "@/store/uiStore";

export function ChatSidebar() {
  const sessions = useChatStore((s) => s.sessions);
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const createSession = useChatStore((s) => s.createSession);
  const setActiveSession = useChatStore((s) => s.setActiveSession);
  const deleteSession = useChatStore((s) => s.deleteSession);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);

  const handleSelect = (id: string) => {
    setActiveSession(id);
    setSidebarOpen(false);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="p-3 border-b">
        <Button
          onClick={() => {
            createSession();
            setSidebarOpen(false);
          }}
          className="w-full justify-start gap-2"
          variant="outline"
          size="sm"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      {/* Session list */}
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          <AnimatePresence mode="popLayout">
            {sessions.map((session) => (
              <motion.div
                key={session.id}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -12 }}
                layout
              >
                <button
                  onClick={() => handleSelect(session.id)}
                  className={cn(
                    "w-full flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-left transition-colors group",
                    activeSessionId === session.id
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent"
                  )}
                >
                  <MessageSquare className="h-4 w-4 shrink-0" />
                  <span className="truncate flex-1">
                    {session.title || "New Chat"}
                  </span>
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteSession(session.id);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.stopPropagation();
                        deleteSession(session.id);
                      }
                    }}
                    className="opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                  </span>
                </button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </ScrollArea>
    </div>
  );
}
