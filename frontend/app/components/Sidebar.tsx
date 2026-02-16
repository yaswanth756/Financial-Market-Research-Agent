'use client';

import { useEffect, useState } from 'react';
import {
    MessageSquare,
    Plus,
    Settings,
    User,
    PieChart,
    Briefcase,
    TrendingUp,
    TrendingDown,
    Activity,
    Trash2,
    Clock,
} from 'lucide-react';
import SettingsModal from './SettingsModal';

interface Session {
    id: string;
    title: string;
    messages: { role: string; content: string }[];
    routeEmoji: string;
    symbols: string[];
    createdAt: number;
}

interface SidebarProps {
    isOpen: boolean;
    sessions: Session[];
    activeSessionId: string | null;
    onNewChat: () => void;
    onSelectSession: (id: string) => void;
    onDeleteSession: (id: string) => void;
}

interface PortfolioItem {
    symbol: string;
    name: string;
    sector: string;
}

function timeAgo(ts: number): string {
    const diff = Date.now() - ts;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'now';
    if (mins < 60) return `${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h`;
    return `${Math.floor(hrs / 24)}d`;
}

export default function Sidebar({ isOpen, sessions, activeSessionId, onNewChat, onSelectSession, onDeleteSession }: SidebarProps) {
    const [portfolio, setPortfolio] = useState<PortfolioItem[]>([]);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    // Fetch portfolio
    const fetchPortfolio = () => {
        fetch('http://localhost:5001/api/portfolio')
            .then(res => res.json())
            .then(data => {
                if (data.stocks) setPortfolio(data.stocks);
            })
            .catch(err => console.error("Sidebar fetch error", err));
    };

    useEffect(() => {
        fetchPortfolio();
        window.addEventListener('focus', fetchPortfolio);
        return () => window.removeEventListener('focus', fetchPortfolio);
    }, []);

    useEffect(() => {
        if (!isSettingsOpen) fetchPortfolio();
    }, [isSettingsOpen]);

    return (
        <>
            <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

            <div
                className={`
            flex flex-col h-screen bg-black border-r border-zinc-800 transition-all duration-300 ease-in-out shrink-0
            ${isOpen ? 'w-[280px] translate-x-0' : 'w-0 -translate-x-full opacity-0 overflow-hidden'}
          `}
            >
                {/* Header / New Chat */}
                <div className="p-4 space-y-4">
                    <button
                        className="flex items-center justify-center gap-2 w-full px-4 py-3 rounded-xl bg-white text-black hover:bg-zinc-200 shadow-lg shadow-white/5 transition-all font-medium text-sm group"
                        onClick={onNewChat}
                    >
                        <Plus size={18} className="group-hover:rotate-90 transition-transform" />
                        <span>New Analysis</span>
                    </button>
                </div>

                {/* Navigation / History */}
                <div className="flex-1 overflow-y-auto px-3 py-2 space-y-6 custom-scrollbar">

                    {/* Section: Session History (Dynamic) */}
                    <div>
                        <div className="text-[11px] font-bold text-zinc-500 mb-3 px-3 uppercase tracking-widest flex items-center justify-between">
                            <span>Recent History</span>
                            <div className="flex items-center gap-1.5">
                                {sessions.length > 0 && (
                                    <span className="text-[9px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded-full font-bold">{sessions.length}</span>
                                )}
                                <Clock size={12} />
                            </div>
                        </div>
                        <div className="space-y-0.5">
                            {sessions.length > 0 ? (
                                sessions.map((session) => {
                                    const isActive = session.id === activeSessionId;
                                    const msgCount = session.messages.filter(m => m.role === 'user').length;
                                    return (
                                        <div
                                            key={session.id}
                                            onClick={() => onSelectSession(session.id)}
                                            role="button"
                                            tabIndex={0}
                                            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelectSession(session.id); }}
                                            className={`flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg transition-all text-sm group text-left relative cursor-pointer
                                                ${isActive
                                                    ? 'bg-zinc-800/80 text-zinc-100 border border-zinc-700/50'
                                                    : 'hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 border border-transparent'
                                                }`}
                                        >
                                            <span className="shrink-0 text-base">{session.routeEmoji}</span>
                                            <div className="flex-1 min-w-0">
                                                <div className={`truncate text-[13px] ${isActive ? 'font-semibold' : ''}`}>
                                                    {session.title}
                                                </div>
                                                <div className="flex items-center gap-1.5 mt-0.5">
                                                    <span className="text-[10px] text-zinc-600">{timeAgo(session.createdAt)}</span>
                                                    {msgCount > 0 && (
                                                        <span className="text-[9px] text-zinc-600">· {msgCount} {msgCount === 1 ? 'msg' : 'msgs'}</span>
                                                    )}
                                                    {session.symbols && session.symbols.length > 0 && (
                                                        <>
                                                            <span className="text-[9px] text-zinc-700">·</span>
                                                            {session.symbols.slice(0, 2).map((sym, j) => (
                                                                <span key={j} className="text-[9px] bg-zinc-800/80 text-zinc-500 px-1 py-0.5 rounded font-medium">{sym}</span>
                                                            ))}
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                            {/* Delete button */}
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    onDeleteSession(session.id);
                                                }}
                                                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-zinc-700 text-zinc-600 hover:text-red-400 transition-all shrink-0"
                                                title="Delete"
                                            >
                                                <Trash2 size={13} />
                                            </button>
                                        </div>
                                    );
                                })
                            ) : (
                                <div className="px-3 py-6 text-xs text-zinc-600 italic text-center">
                                    <MessageSquare size={20} className="mx-auto mb-2 text-zinc-700" />
                                    <div>No conversations yet.</div>
                                    <div className="mt-1 text-zinc-700">Click "New Analysis" to start!</div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Section: Your Portfolio */}
                    <div>
                        <div className="text-[11px] font-bold text-zinc-500 mb-3 px-3 uppercase tracking-widest flex items-center justify-between group cursor-pointer" onClick={() => setIsSettingsOpen(true)}>
                            <span>Your Portfolio</span>
                            <Settings size={12} className="group-hover:text-white transition-colors" />
                        </div>
                        <div className="space-y-1">
                            {portfolio.length > 0 ? (
                                portfolio.map((stock, i) => (
                                    <div key={i} className="group flex items-center gap-2 w-full px-2 py-2 rounded-lg hover:bg-zinc-900/50 transition-colors text-zinc-400 hover:text-zinc-200 cursor-pointer text-sm">
                                        <div className={`w-1.5 h-1.5 rounded-full ${i % 2 === 0 ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]'}`} />
                                        <span className="font-medium text-zinc-300 w-12">{stock.symbol}</span>
                                    </div>
                                ))
                            ) : (
                                <div className="px-3 text-xs text-zinc-600 italic">No stocks added.</div>
                            )}

                            <button
                                onClick={() => setIsSettingsOpen(true)}
                                className="w-full mt-2 py-2 px-3 text-xs text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/30 rounded-lg flex items-center justify-center gap-2 transition-all border border-dashed border-zinc-800 hover:border-zinc-700"
                            >
                                <Plus size={12} />
                                Add Stock
                            </button>
                        </div>
                    </div>

                    {/* Section: Watchlist */}
                    <div>
                        <div className="text-[11px] font-bold text-zinc-500 mb-3 px-3 uppercase tracking-widest flex items-center justify-between">
                            <span>Watchlist</span>
                            <Activity size={12} />
                        </div>
                        <div className="space-y-1">
                            <div className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-zinc-900/50 text-xs text-zinc-400">
                                <span>NIFTY 50</span>
                                <span className="text-emerald-400 font-medium">+0.45%</span>
                            </div>
                            <div className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-zinc-900/50 text-xs text-zinc-400">
                                <span>BANK NIFTY</span>
                                <span className="text-red-400 font-medium">-0.12%</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer / User Profile */}
                <div className="p-4 border-t border-zinc-900 bg-zinc-950/50">
                    <button
                        onClick={() => setIsSettingsOpen(true)}
                        className="flex items-center gap-3 w-full p-2 rounded-xl hover:bg-zinc-900 transition-colors text-zinc-300 group"
                    >
                        <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
                            <User size={16} />
                        </div>
                        <div className="text-sm font-medium text-left flex-1 min-w-0">
                            <div className="truncate text-zinc-200">Alexander</div>
                            <div className="text-[10px] text-emerald-400 font-semibold uppercase tracking-wider">Pro Plan Active</div>
                        </div>
                        <Settings size={16} className="text-zinc-600 group-hover:text-zinc-400 transition-colors" />
                    </button>
                </div>
            </div>
        </>
    );
}
