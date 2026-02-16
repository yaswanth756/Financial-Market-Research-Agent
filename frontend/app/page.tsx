'use client';

import { useState, useCallback } from 'react';
import Sidebar from "./components/Sidebar";
import ChatInterface from "./components/ChatInterface";

interface Message {
  role: 'user' | 'assistant';
  content: string;
  isError?: boolean;
  route?: string;
  routeLabel?: string;
  routeEmoji?: string;
  mode?: string;
  confidence?: string;
  confidenceReasons?: string[];
  contradictions?: string[];
  isFollowUp?: boolean;
  elapsed?: number;
  sourcesCount?: number;
  symbols?: string[];
  typingId?: string;
}

interface Session {
  id: string;
  title: string;
  messages: Message[];
  routeEmoji: string;
  symbols: string[];
  createdAt: number;
}

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

function generateTitle(query: string): string {
  const q = query.replace(/^☀️\s*/, '').trim();
  return q.length > 40 ? q.slice(0, 40) + '…' : q;
}

export default function Home() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Get active session
  const activeSession = sessions.find(s => s.id === activeSessionId) || null;
  const activeMessages = activeSession?.messages || [];

  // Create new session
  const handleNewChat = useCallback(() => {
    const newSession: Session = {
      id: generateId(),
      title: 'New Analysis',
      messages: [],
      routeEmoji: '🤖',
      symbols: [],
      createdAt: Date.now(),
    };
    setSessions(prev => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
  }, []);

  // Switch to existing session
  const handleSelectSession = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId);
  }, []);

  // Delete a session
  const handleDeleteSession = useCallback((sessionId: string) => {
    setSessions(prev => prev.filter(s => s.id !== sessionId));
    if (activeSessionId === sessionId) {
      setActiveSessionId(null);
    }
  }, [activeSessionId]);

  // Update messages for active session (called from ChatInterface)
  const handleSetMessages = useCallback((updater: Message[] | ((prev: Message[]) => Message[])) => {
    setSessions(prev => prev.map(s => {
      if (s.id !== activeSessionId) return s;

      const newMessages = typeof updater === 'function' ? updater(s.messages) : updater;

      // Auto-update session title & metadata from first user message
      const firstUserMsg = newMessages.find(m => m.role === 'user');
      const lastAssistantMsg = [...newMessages].reverse().find(m => m.role === 'assistant' && !m.isError);

      return {
        ...s,
        messages: newMessages,
        title: firstUserMsg ? generateTitle(firstUserMsg.content) : s.title,
        routeEmoji: lastAssistantMsg?.routeEmoji || s.routeEmoji,
        symbols: lastAssistantMsg?.symbols || s.symbols,
      };
    }));
  }, [activeSessionId]);

  // Auto-create first session if user starts typing with no session
  const ensureActiveSession = useCallback(() => {
    if (!activeSessionId) {
      const newSession: Session = {
        id: generateId(),
        title: 'New Analysis',
        messages: [],
        routeEmoji: '🤖',
        symbols: [],
        createdAt: Date.now(),
      };
      setSessions(prev => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      return newSession.id;
    }
    return activeSessionId;
  }, [activeSessionId]);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-black text-white selection:bg-zinc-800 selection:text-white">
      <Sidebar
        isOpen={isSidebarOpen}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
      />
      <ChatInterface
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        messages={activeMessages}
        setMessages={handleSetMessages}
        ensureActiveSession={ensureActiveSession}
      />
    </div>
  );
}
