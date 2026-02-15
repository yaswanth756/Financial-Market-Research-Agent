'use client';

import { useState, useRef, useEffect } from 'react';
import {
    Paperclip,
    MoveRight,
    Sparkles,
    PanelLeftClose,
    PanelLeftOpen,
    MoreHorizontal,
    TrendingUp,
    BarChart3,
    Newspaper,
    Briefcase,
    AlertCircle,
    ArrowUpRight,
    ArrowDownRight,
    Target,
    GitCompareArrows,
    CandlestickChart,
    Search,
    Globe,
    Bitcoin,
    DollarSign
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Ticker from './Ticker';

const API_BASE = 'http://localhost:5001';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    isError?: boolean;
    route?: string;
    routeLabel?: string;
    routeEmoji?: string;
}

interface ChatInterfaceProps {
    isSidebarOpen: boolean;
    onToggleSidebar: () => void;
}

// Professional suggestion prompts covering all capabilities
const SUGGESTIONS = [
    {
        icon: <DollarSign size={18} className="text-emerald-400" />,
        title: "Stock Price",
        prompt: "What's the current stock price of Apple?",
        color: "emerald",
    },
    {
        icon: <Target size={18} className="text-orange-400" />,
        title: "Analyst Ratings",
        prompt: "Show me analyst recommendations for Tesla",
        color: "orange",
    },
    {
        icon: <BarChart3 size={18} className="text-blue-400" />,
        title: "Fundamentals",
        prompt: "What are the fundamentals of Microsoft stock?",
        color: "blue",
    },
    {
        icon: <GitCompareArrows size={18} className="text-violet-400" />,
        title: "Compare Stocks",
        prompt: "Compare the performance of Google and Amazon stocks",
        color: "violet",
    },
    {
        icon: <CandlestickChart size={18} className="text-cyan-400" />,
        title: "Technical Analysis",
        prompt: "Technical analysis of Reliance",
        color: "cyan",
    },
    {
        icon: <Newspaper size={18} className="text-amber-400" />,
        title: "Financial News",
        prompt: "Get the latest financial news about cryptocurrency",
        color: "amber",
    },
    {
        icon: <Briefcase size={18} className="text-purple-400" />,
        title: "Portfolio Analysis",
        prompt: "How is my portfolio doing today?",
        color: "purple",
    },
    {
        icon: <Globe size={18} className="text-sky-400" />,
        title: "Market Overview",
        prompt: "How is the market today? What's moving?",
        color: "sky",
    },
];

// Route badge colors
const ROUTE_COLORS: Record<string, string> = {
    'STOCK_PRICE': 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    'RECOMMENDATIONS': 'bg-orange-500/15 text-orange-400 border-orange-500/30',
    'FUNDAMENTALS': 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    'COMPARISON': 'bg-violet-500/15 text-violet-400 border-violet-500/30',
    'TECHNICALS': 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
    'NEWS_SEARCH': 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    'PORTFOLIO': 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    'DISCOVERY': 'bg-pink-500/15 text-pink-400 border-pink-500/30',
    'GENERAL': 'bg-sky-500/15 text-sky-400 border-sky-500/30',
    'CHAT': 'bg-zinc-500/15 text-zinc-400 border-zinc-500/30',
};

export default function ChatInterface({ isSidebarOpen, onToggleSidebar }: ChatInterfaceProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isConnected, setIsConnected] = useState<boolean | null>(null);
    const [currentRoute, setCurrentRoute] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    // Check backend health on mount
    useEffect(() => {
        const checkHealth = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/health`);
                if (res.ok) {
                    setIsConnected(true);
                } else {
                    setIsConnected(false);
                }
            } catch {
                setIsConnected(false);
            }
        };
        checkHealth();
    }, []);

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        const query = input.trim();
        if (!query || isLoading) return;

        // Check for special commands
        if (query === '/briefing') {
            setInput('');
            await fetchMorningBriefing();
            return;
        }

        const userMsg: Message = { role: 'user', content: query };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);
        setCurrentRoute(null);

        try {
            const res = await fetch(`${API_BASE}/api/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query }),
            });

            const data = await res.json();

            if (data.success) {
                const aiMsg: Message = {
                    role: 'assistant',
                    content: data.report,
                    route: data.route,
                    routeLabel: data.route_label,
                    routeEmoji: data.route_emoji,
                };
                setMessages(prev => [...prev, aiMsg]);
                setCurrentRoute(data.route);
            } else {
                const errMsg: Message = {
                    role: 'assistant',
                    content: `⚠️ **Analysis Error**\n\n${data.error || 'Something went wrong. Please try again.'}`,
                    isError: true
                };
                setMessages(prev => [...prev, errMsg]);
            }
        } catch (err) {
            const errMsg: Message = {
                role: 'assistant',
                content: '⚠️ **Connection Error**\n\nCould not reach the backend server. Make sure `api.py` is running on port 5001.',
                isError: true
            };
            setMessages(prev => [...prev, errMsg]);
        } finally {
            setIsLoading(false);
        }
    };

    const fetchMorningBriefing = async () => {
        const userMsg: Message = { role: 'user', content: '☀️ Morning Briefing' };
        setMessages(prev => [...prev, userMsg]);
        setIsLoading(true);

        try {
            const res = await fetch(`${API_BASE}/api/morning-briefing`);
            const data = await res.json();

            if (data.success) {
                const aiMsg: Message = {
                    role: 'assistant',
                    content: data.report,
                    route: data.route,
                    routeLabel: data.route_label,
                    routeEmoji: data.route_emoji,
                };
                setMessages(prev => [...prev, aiMsg]);
            } else {
                const errMsg: Message = {
                    role: 'assistant',
                    content: `⚠️ **Briefing Error**\n\n${data.error || 'Could not generate morning briefing.'}`,
                    isError: true
                };
                setMessages(prev => [...prev, errMsg]);
            }
        } catch {
            const errMsg: Message = {
                role: 'assistant',
                content: '⚠️ **Connection Error**\n\nCould not reach the backend server.',
                isError: true
            };
            setMessages(prev => [...prev, errMsg]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSuggestionClick = (prompt: string) => {
        if (prompt === '/briefing') {
            fetchMorningBriefing();
        } else {
            setInput(prompt);
            // Submit after a tick so input is set
            setTimeout(() => {
                const form = document.getElementById('chat-form') as HTMLFormElement;
                form?.requestSubmit();
            }, 50);
        }
    };

    const hasMessages = messages.length > 0;

    return (
        <div className="flex flex-col flex-1 h-full bg-zinc-950 text-zinc-100 relative overflow-hidden">

            {/* Live Ticker Bar */}
            <div className="border-b border-zinc-800/40 bg-zinc-950/30 backdrop-blur-sm z-30 sticky top-0">
                <Ticker />
            </div>

            {/* Header */}
            <header className="flex items-center justify-between px-4 py-3 border-b border-zinc-800/60 bg-zinc-950/90 backdrop-blur-md sticky top-10 z-20">
                <div className="flex items-center gap-3">
                    <button
                        onClick={onToggleSidebar}
                        className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
                        title={isSidebarOpen ? "Close Sidebar" : "Open Sidebar"}
                    >
                        {isSidebarOpen ? <PanelLeftClose size={20} /> : <PanelLeftOpen size={20} />}
                    </button>

                    <div className="flex items-center gap-2.5">
                        <div className="bg-gradient-to-br from-blue-500 to-indigo-600 w-7 h-7 rounded-lg flex items-center justify-center shadow-lg shadow-blue-500/20">
                            <Sparkles size={14} className="text-white" />
                        </div>
                        <span className="font-semibold text-base text-zinc-100">MarketMind AI</span>
                        <span className="px-2 py-0.5 rounded-full bg-zinc-800 text-[10px] uppercase font-bold text-zinc-400 border border-zinc-700/50 tracking-wider">PRO</span>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    {/* Connection status indicator */}
                    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs ${isConnected === true
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : isConnected === false
                            ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                            : 'bg-zinc-800 text-zinc-500 border border-zinc-700/50'
                        }`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${isConnected === true ? 'bg-emerald-400' : isConnected === false ? 'bg-red-400' : 'bg-zinc-500'
                            }`} />
                        {isConnected === true ? 'Live' : isConnected === false ? 'Offline' : 'Connecting...'}
                    </div>
                    <button className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors">
                        <MoreHorizontal size={18} />
                    </button>
                </div>
            </header>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto scroll-smooth pb-16 custom-scrollbar">
                {!hasMessages ? (
                    /* Empty State - Professional Welcome Screen */
                    <div className="flex flex-col items-center justify-center h-full px-4 pb-32 pt-28">
                        <div className="max-w-3xl w-full text-center space-y-8">
                            {/* Logo & Title */}
                            <div className="space-y-4">
                                <div className="bg-gradient-to-br from-blue-500 to-indigo-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto shadow-2xl shadow-blue-500/30 ring-4 ring-zinc-900 ring-offset-2 ring-offset-zinc-800">
                                    <Sparkles size={32} className="text-white" />
                                </div>
                                <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white via-zinc-200 to-zinc-500 pb-1">
                                    Your All-Rounder Financial Agent
                                </h2>
                                <p className="text-sm text-zinc-400 max-w-lg mx-auto leading-relaxed">
                                    Powered by <span className="text-zinc-200 font-medium">Gemini 2.5</span> + <span className="text-zinc-200 font-medium">Real-time Market Data</span>.
                                    Stocks, crypto, fundamentals, technicals, news — all in one place.
                                </p>
                                {/* Coverage badges */}
                                <div className="flex items-center justify-center gap-2 flex-wrap">
                                    <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-bold uppercase tracking-wider border border-emerald-500/20">Indian NSE</span>
                                    <span className="px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 text-[10px] font-bold uppercase tracking-wider border border-blue-500/20">US NYSE/NASDAQ</span>
                                    <span className="px-2.5 py-1 rounded-full bg-orange-500/10 text-orange-400 text-[10px] font-bold uppercase tracking-wider border border-orange-500/20">Crypto</span>
                                    <span className="px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 text-[10px] font-bold uppercase tracking-wider border border-amber-500/20">Commodities</span>
                                </div>
                            </div>

                            {/* Suggestion Cards */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-left">
                                {SUGGESTIONS.map((s, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleSuggestionClick(s.prompt)}
                                        className="flex items-start gap-3 p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-800/60 hover:bg-zinc-800/60 hover:border-zinc-700 transition-all text-left group backdrop-blur-sm"
                                    >
                                        <div className="p-2 rounded-lg bg-zinc-800/50 group-hover:bg-zinc-700/50 transition-colors shrink-0 border border-zinc-700/30">
                                            {s.icon}
                                        </div>
                                        <div className="min-w-0">
                                            <div className="text-xs font-semibold text-zinc-200 group-hover:text-white transition-colors">{s.title}</div>
                                            <div className="text-[11px] text-zinc-500 mt-0.5 line-clamp-2 leading-relaxed group-hover:text-zinc-400 transition-colors">
                                                {s.prompt}
                                            </div>
                                        </div>
                                    </button>
                                ))}
                            </div>

                            {/* Quick action: Morning Briefing */}
                            <button
                                onClick={() => handleSuggestionClick('/briefing')}
                                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20 hover:border-amber-500/40 text-amber-400 text-sm font-medium transition-all hover:shadow-lg hover:shadow-amber-500/5"
                            >
                                ☀️ Get Morning Briefing
                            </button>
                        </div>
                    </div>
                ) : (
                    /* Messages List */
                    <div className="max-w-3xl mx-auto w-full p-4 md:p-6 space-y-8 pb-40">
                        {messages.map((msg, idx) => (
                            <div
                                key={idx}
                                className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div
                                    className={`
                    max-w-[90%] md:max-w-[85%] text-sm leading-7
                    ${msg.role === 'user'
                                            ? 'bg-zinc-800 text-white px-5 py-3 rounded-2xl rounded-tr-sm shadow-sm'
                                            : msg.isError
                                                ? 'bg-red-500/5 border border-red-500/20 text-red-300 px-5 py-3.5 rounded-2xl rounded-tl-sm'
                                                : 'text-zinc-300 px-2 py-1'
                                        }
                  `}
                                >
                                    {/* Route Badge for AI responses */}
                                    {msg.role === 'assistant' && msg.route && !msg.isError && (
                                        <div className="mb-3">
                                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider border ${ROUTE_COLORS[msg.route] || ROUTE_COLORS['GENERAL']}`}>
                                                <span>{msg.routeEmoji}</span>
                                                <span>{msg.routeLabel}</span>
                                            </span>
                                        </div>
                                    )}

                                    {msg.role === 'assistant' ? (
                                        <div className="prose prose-invert prose-sm max-w-none 
                      prose-headings:text-zinc-100 prose-headings:font-bold prose-headings:mb-3 prose-headings:mt-6
                      prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
                      prose-p:text-zinc-300 prose-p:leading-7 prose-p:mb-4
                      prose-strong:text-white prose-strong:font-semibold
                      prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline
                      prose-code:text-emerald-300 prose-code:bg-zinc-900/50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:border prose-code:border-zinc-800
                      prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-800 prose-pre:rounded-xl prose-pre:p-4
                      prose-ul:text-zinc-300 prose-ul:my-4 prose-li:my-1
                      prose-hr:border-zinc-800 prose-hr:my-6
                      prose-blockquote:border-l-4 prose-blockquote:border-blue-500/50 prose-blockquote:bg-blue-500/5 prose-blockquote:px-4 prose-blockquote:py-1 prose-blockquote:rounded-r-lg prose-blockquote:italic prose-blockquote:text-zinc-400
                      prose-table:border-collapse prose-th:border prose-th:border-zinc-700 prose-th:bg-zinc-800/50 prose-th:px-3 prose-th:py-2 prose-th:text-zinc-200 prose-th:text-xs prose-th:font-semibold
                      prose-td:border prose-td:border-zinc-800 prose-td:px-3 prose-td:py-2 prose-td:text-zinc-300 prose-td:text-xs
                    ">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                                        </div>
                                    ) : (
                                        msg.content
                                    )}
                                </div>
                            </div>
                        ))}

                        {isLoading && (
                            <div className="flex justify-start w-full animate-pulse">
                                <div className="px-4 py-2 w-fit flex gap-3 items-center">
                                    <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 animate-bounce">
                                        <Sparkles size={16} className="text-white" />
                                    </div>
                                    <div className="space-y-2">
                                        <div className="h-4 w-32 bg-zinc-800/50 rounded-full" />
                                        <div className="h-3 w-48 bg-zinc-800/30 rounded-full" />
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className={`${hasMessages ? 'absolute bottom-0 left-0 right-0 bg-gradient-to-t from-zinc-950 via-zinc-950 to-transparent pt-12 pb-6' : ''} px-4`}>
                <div className="max-w-3xl mx-auto w-full relative group">
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                    <form
                        id="chat-form"
                        onSubmit={handleSend}
                        className="relative flex items-end gap-2 bg-zinc-900 border border-zinc-700/60 rounded-2xl p-2 shadow-2xl shadow-black/60 focus-within:ring-1 focus-within:ring-zinc-600 focus-within:border-zinc-600 transition-all"
                    >
                        <button
                            type="button"
                            className="p-3 text-zinc-500 hover:text-white transition-colors rounded-xl hover:bg-zinc-800"
                            title="Attach file"
                        >
                            <Paperclip size={20} />
                        </button>

                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Ask about any stock, crypto, or market trend..."
                            className="flex-1 bg-transparent border-none outline-none text-white py-3.5 px-2 placeholder:text-zinc-500 text-sm font-medium"
                            disabled={isLoading}
                        />

                        <button
                            type="submit"
                            disabled={!input.trim() || isLoading}
                            className={`
                        p-3 rounded-xl transition-all duration-200 flex items-center justify-center
                        ${input.trim() && !isLoading
                                    ? 'bg-white text-black hover:bg-zinc-200 shadow-lg hover:translate-x-0.5'
                                    : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'}
                    `}
                        >
                            <MoveRight size={20} />
                        </button>
                    </form>
                    <div className="text-center mt-3 text-xs text-zinc-600 font-medium">
                        MarketMind AI &middot; 10 Smart Routes &middot; Indian + US + Crypto + Commodities
                    </div>
                </div>
            </div>

        </div>
    );
}
