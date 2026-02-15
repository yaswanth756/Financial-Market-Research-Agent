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
    Activity
} from 'lucide-react';
import SettingsModal from './SettingsModal';

interface SidebarProps {
    isOpen: boolean;
}

interface PortfolioItem {
    symbol: string;
    name: string;
    sector: string;
}

export default function Sidebar({ isOpen }: SidebarProps) {
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

    // Initial fetch + re-fetch on focus (in case edited in another tab)
    useEffect(() => {
        fetchPortfolio();
        window.addEventListener('focus', fetchPortfolio);
        return () => window.removeEventListener('focus', fetchPortfolio);
    }, []);

    // Also re-fetch when settings modal closes
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
                        onClick={() => window.location.reload()}
                    >
                        <Plus size={18} className="group-hover:rotate-90 transition-transform" />
                        <span>New Analysis</span>
                    </button>
                </div>

                {/* Navigation / History */}
                <div className="flex-1 overflow-y-auto px-3 py-2 space-y-6 custom-scrollbar">

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

                    {/* Section: Recent Chats */}
                    <div>
                        <div className="text-[11px] font-bold text-zinc-500 mb-3 px-3 uppercase tracking-widest flex items-center justify-between">
                            <span>Recent History</span>
                            <MessageSquare size={12} />
                        </div>
                        <div className="space-y-1">
                            {['Morning Briefing (Today)', 'TCS Earnings Analysis', 'HDFC Bank Strategy'].map((item, i) => (
                                <button
                                    key={i}
                                    className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg hover:bg-zinc-900 transition-colors text-zinc-400 hover:text-zinc-200 text-sm group text-left"
                                >
                                    <span className="truncate flex-1">{item}</span>
                                    <span className="opacity-0 group-hover:opacity-100 text-xs text-zinc-600 transition-opacity">
                                        {i === 0 ? '2h' : '1d'}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Section: Watchlist (Static Demo) */}
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
                    {/* Sign out hint */}
                    <div className="text-[10px] text-center text-zinc-600 mt-2 opacity-0 group-hover:opacity-50 transition-opacity">
                        Click to manage profile
                    </div>
                </div>
            </div>
        </>
    );
}
