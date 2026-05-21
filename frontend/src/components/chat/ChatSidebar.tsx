"use client";

import { useState } from "react";
import { Plus, MessageSquare, Trash2, Pencil, Check, X, Car } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/store/chatStore";
import { useUIStore } from "@/store/uiStore";

export function ChatSidebar() {
  const sessions = useChatStore((s) => s.sessions);
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const createSession = useChatStore((s) => s.createSession);
  const setActiveSession = useChatStore((s) => s.setActiveSession);
  const deleteSession = useChatStore((s) => s.deleteSession);
  const renameSession = useChatStore((s) => s.renameSession);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const handleSelect = (id: string) => {
    setActiveSession(id);
    setSidebarOpen(false);
  };

  const startRename = (id: string, currentTitle: string) => {
    setEditingId(id);
    setEditValue(currentTitle);
  };

  const confirmRename = () => {
    if (editingId && editValue.trim()) {
      renameSession(editingId, editValue.trim());
    }
    setEditingId(null);
  };

  const cancelRename = () => {
    setEditingId(null);
  };

  // Group sessions by date
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  const groups: { label: string; items: typeof sessions }[] = [];
  const todayItems = sessions.filter((s) => new Date(s.timestamp) >= today);
  const yesterdayItems = sessions.filter(
    (s) => new Date(s.timestamp) >= yesterday && new Date(s.timestamp) < today
  );
  const olderItems = sessions.filter(
    (s) => new Date(s.timestamp) < yesterday
  );

  if (todayItems.length) groups.push({ label: "Today", items: todayItems });
  if (yesterdayItems.length) groups.push({ label: "Yesterday", items: yesterdayItems });
  if (olderItems.length) groups.push({ label: "Previous", items: olderItems });

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="p-3 border-b shrink-0">
        <Button
          onClick={() => {
            createSession();
            setSidebarOpen(false);
          }}
          className="w-full justify-start gap-2 rounded-xl h-10 shadow-sm"
          variant="outline"
          size="sm"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      {/* Session list — independent scroll */}
      <div className="flex-1 overflow-y-auto min-h-0 scrollbar-thin">
        <div className="p-2 space-y-3">
          {groups.map((group) => (
            <div key={group.label}>
              <p className="text-[10px] font-semibold text-muted-foreground/60 px-3 py-1.5 uppercase tracking-widest">
                {group.label}
              </p>
              <div className="space-y-0.5">
                <AnimatePresence mode="popLayout">
                  {group.items.map((session) => (
                    <motion.div
                      key={session.id}
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -12 }}
                      layout
                    >
                      {editingId === session.id ? (
                        <div className="flex items-center gap-1 px-2 py-1">
                          <input
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") confirmRename();
                              if (e.key === "Escape") cancelRename();
                            }}
                            className="flex-1 text-sm bg-transparent border rounded-lg px-2 py-1 outline-none focus:border-primary"
                            autoFocus
                          />
                          <button onClick={confirmRename} className="p-1 hover:text-primary">
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={cancelRename} className="p-1 hover:text-destructive">
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleSelect(session.id)}
                          className={cn(
                            "w-full flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm text-left transition-all duration-200 group",
                            activeSessionId === session.id
                              ? "bg-primary/10 text-primary shadow-sm"
                              : "text-muted-foreground hover:bg-accent/80"
                          )}
                        >
                          <MessageSquare className={cn(
                            "h-4 w-4 shrink-0 transition-colors",
                            activeSessionId === session.id
                              ? "text-primary"
                              : "text-muted-foreground/50"
                          )} />
                          <span className="truncate flex-1 text-[13px]">
                            {session.title || "New Chat"}
                          </span>
                          <span className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-0.5 shrink-0">
                            <span
                              role="button"
                              tabIndex={0}
                              onClick={(e) => {
                                e.stopPropagation();
                                startRename(session.id, session.title);
                              }}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  e.stopPropagation();
                                  startRename(session.id, session.title);
                                }
                              }}
                              className="cursor-pointer p-1 rounded-md hover:bg-accent"
                            >
                              <Pencil className="h-3 w-3 text-muted-foreground hover:text-primary" />
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
                              className="cursor-pointer p-1 rounded-md hover:bg-destructive/10"
                            >
                              <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                            </span>
                          </span>
                        </button>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>
          ))}
          {sessions.length === 0 && (
            <div className="flex flex-col items-center py-12 px-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted mb-3">
                <Car className="h-5 w-5 text-muted-foreground/50" />
              </div>
              <p className="text-xs text-muted-foreground text-center">
                No conversations yet.
              </p>
              <p className="text-[10px] text-muted-foreground/60 text-center mt-0.5">
                Click &quot;New Chat&quot; to start.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
