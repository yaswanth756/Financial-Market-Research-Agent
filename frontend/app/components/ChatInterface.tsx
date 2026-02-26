'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
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
    DollarSign,
    Zap,
    Microscope,
    ShieldAlert,
    CheckCircle2,
    AlertTriangle,
    XCircle,
    Clock,
    Database,
    Brain,
    ChevronDown,
    Reply,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Ticker from './Ticker';

const API_BASE = 'http://localhost:5001';

type AnalysisMode = 'auto' | 'quick' | 'deep';

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
    typingId?: string; // Unique ID for typewriter animation
}

interface ChatInterfaceProps {
    isSidebarOpen: boolean;
    onToggleSidebar: () => void;
    messages: Message[];
    setMessages: (updater: Message[] | ((prev: Message[]) => Message[])) => void;
    ensureActiveSession: () => string;
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
        icon: <Brain size={18} className="text-pink-400" />,
        title: "Deep Analysis",
        prompt: "Generate a bull and bear case for HDFC Bank",
        color: "pink",
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
    'SUGGESTION': 'bg-rose-500/15 text-rose-400 border-rose-500/30',
};

// Confidence badge component
function ConfidenceBadge({ level, reasons }: { level: string; reasons?: string[] }) {
    const [showDetails, setShowDetails] = useState(false);
    const config: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
        HIGH: { icon: <CheckCircle2 size={12} />, color: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', label: 'High Confidence' },
        MEDIUM: { icon: <AlertTriangle size={12} />, color: 'bg-amber-500/15 text-amber-400 border-amber-500/30', label: 'Medium Confidence' },
        LOW: { icon: <XCircle size={12} />, color: 'bg-red-500/15 text-red-400 border-red-500/30', label: 'Low Confidence' },
    };
    const c = config[level] || config.MEDIUM;

    return (
        <div className="relative inline-block">
            <button
                onClick={() => reasons?.length && setShowDetails(!showDetails)}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${c.color} ${reasons?.length ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}`}
            >
                {c.icon}
                <span>{c.label}</span>
                {reasons?.length ? <ChevronDown size={10} className={`transition-transform ${showDetails ? 'rotate-180' : ''}`} /> : null}
            </button>
            {showDetails && reasons && (
                <div className="absolute top-full left-0 mt-1 z-50 w-64 bg-zinc-900 border border-zinc-700 rounded-lg p-3 shadow-xl">
                    <div className="text-[11px] text-zinc-400 space-y-1">
                        {reasons.map((r, i) => (
                            <div key={i} className="flex items-start gap-1.5">
                                <span className="shrink-0 mt-0.5">{r.startsWith('✅') ? '✅' : '⚠️'}</span>
                                <span>{r.replace(/^[✅⚠️]\s*/, '')}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// Mode selector component
function ModeSelector({ mode, onChange }: { mode: AnalysisMode; onChange: (m: AnalysisMode) => void }) {
    const modes: { value: AnalysisMode; label: string; icon: React.ReactNode; desc: string }[] = [
        { value: 'auto', label: 'Auto', icon: <Sparkles size={14} />, desc: 'Auto-detect' },
        { value: 'quick', label: 'Quick', icon: <Zap size={14} />, desc: '<30s' },
        { value: 'deep', label: 'Deep', icon: <Microscope size={14} />, desc: '<3min' },
    ];

    return (
        <div className="flex items-center bg-zinc-800/60 rounded-lg p-0.5 border border-zinc-700/40">
            {modes.map((m) => (
                <button
                    key={m.value}
                    type="button"
                    onClick={() => onChange(m.value)}
                    className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[11px] font-semibold transition-all ${mode === m.value
                        ? m.value === 'deep'
                            ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow-sm'
                            : m.value === 'quick'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-sm'
                                : 'bg-zinc-700 text-zinc-200 border border-zinc-600/50 shadow-sm'
                        : 'text-zinc-500 hover:text-zinc-300 border border-transparent'
                        }`}
                    title={m.desc}
                >
                    {m.icon}
                    <span>{m.label}</span>
                </button>
            ))}
        </div>
    );
}

// ============================================================================
// TYPEWRITER HOOK — Smooth streaming like ChatGPT/Gemini
// ============================================================================
function useTypewriter(fullText: string, enabled: boolean, speed: number = 12) {
    const [displayedText, setDisplayedText] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [isDone, setIsDone] = useState(!enabled);
    const indexRef = useRef(0);
    const rafRef = useRef<number | null>(null);
    const lastTimeRef = useRef(0);

    useEffect(() => {
        if (!enabled || !fullText) {
            setDisplayedText(fullText);
            setIsDone(true);
            setIsTyping(false);
            return;
        }

        // Reset on new text
        indexRef.current = 0;
        setDisplayedText('');
        setIsTyping(true);
        setIsDone(false);
        lastTimeRef.current = 0;

        const totalLen = fullText.length;

        // Adaptive chunk size: bigger text → bigger chunks for smooth feel
        const getChunkSize = () => {
            const progress = indexRef.current / totalLen;
            // Start slow (2-3 chars), ramp up to speed in middle, slow down at end
            if (progress < 0.05) return Math.max(1, Math.floor(speed * 0.3));
            if (progress > 0.95) return Math.max(2, Math.floor(speed * 0.5));
            // Vary chunk size slightly for natural feel
            return speed + Math.floor(Math.random() * 4) - 2;
        };

        // Interval between frames in ms — lower = faster
        const getInterval = () => {
            const progress = indexRef.current / totalLen;
            const char = fullText[indexRef.current] || '';
            // Pause slightly at newlines, headers, and punctuation for natural rhythm
            if (char === '\n') return 30;
            if (char === '#') return 15;
            if ('.!?:'.includes(char)) return 25;
            if (progress < 0.03) return 20; // Start gentle
            return 8; // Fast cruise speed
        };

        const tick = (timestamp: number) => {
            if (indexRef.current >= totalLen) {
                setDisplayedText(fullText);
                setIsTyping(false);
                setIsDone(true);
                return;
            }

            const elapsed = timestamp - lastTimeRef.current;
            const interval = getInterval();

            if (elapsed >= interval) {
                const chunk = getChunkSize();
                indexRef.current = Math.min(indexRef.current + chunk, totalLen);
                setDisplayedText(fullText.slice(0, indexRef.current));
                lastTimeRef.current = timestamp;
            }

            rafRef.current = requestAnimationFrame(tick);
        };

        rafRef.current = requestAnimationFrame(tick);

        return () => {
            if (rafRef.current) cancelAnimationFrame(rafRef.current);
        };
    }, [fullText, enabled, speed]);

    // Skip to end
    const skipToEnd = useCallback(() => {
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
        setDisplayedText(fullText);
        setIsTyping(false);
        setIsDone(true);
    }, [fullText]);

    return { displayedText, isTyping, isDone, skipToEnd };
}

// ============================================================================
// TYPEWRITER MESSAGE COMPONENT
// ============================================================================
function TypewriterMessage({
    msg,
    shouldAnimate,
    onTypingDone,
}: {
    msg: Message;
    shouldAnimate: boolean;
    onTypingDone?: () => void;
}) {
    const { displayedText, isTyping, isDone, skipToEnd } = useTypewriter(
        msg.content,
        shouldAnimate,
        14 // chars per frame — fast but readable
    );

    // Notify parent when typing is done
    useEffect(() => {
        if (isDone && onTypingDone) onTypingDone();
    }, [isDone, onTypingDone]);

    const textToRender = shouldAnimate ? displayedText : msg.content;

    return (
        <div>
            {/* AI Response Header: Route + Mode + Confidence + Follow-up */}
            {msg.role === 'assistant' && !msg.isError && (
                <div className="mb-3 flex flex-wrap items-center gap-2">
                    {/* Route badge */}
                    {msg.route && (
                        <span className={`badge-animate inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider border ${ROUTE_COLORS[msg.route] || ROUTE_COLORS['GENERAL']}`}>
                            <span>{msg.routeEmoji}</span>
                            <span>{msg.routeLabel}</span>
                        </span>
                    )}

                    {/* Mode badge */}
                    {msg.mode && (
                        <span className={`badge-animate inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${msg.mode === 'deep'
                            ? 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30'
                            : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                            }`} style={{ animationDelay: '0.1s' }}>
                            {msg.mode === 'deep' ? <Microscope size={10} /> : <Zap size={10} />}
                            <span>{msg.mode === 'deep' ? 'Deep' : 'Quick'}</span>
                        </span>
                    )}

                    {/* Confidence badge */}
                    {msg.confidence && (
                        <span className="badge-animate" style={{ animationDelay: '0.2s' }}>
                            <ConfidenceBadge level={msg.confidence} reasons={msg.confidenceReasons} />
                        </span>
                    )}

                    {/* Follow-up indicator */}
                    {msg.isFollowUp && (
                        <span className="badge-animate inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-sky-500/15 text-sky-400 border border-sky-500/30" style={{ animationDelay: '0.3s' }}>
                            <Reply size={10} />
                            <span>Follow-up</span>
                        </span>
                    )}
                </div>
            )}

            {/* Contradictions Alert */}
            {msg.role === 'assistant' && msg.contradictions && msg.contradictions.length > 0 && (
                <div className="mb-3 bg-amber-500/5 border border-amber-500/20 rounded-lg p-3">
                    <div className="flex items-center gap-1.5 text-amber-400 text-[11px] font-bold uppercase tracking-wider mb-1.5">
                        <ShieldAlert size={13} />
                        <span>Contradictions Detected</span>
                    </div>
                    {msg.contradictions.map((c, i) => (
                        <div key={i} className="text-[12px] text-amber-300/80 leading-relaxed">
                            {c.replace(/^⚠️\s*/, '')}
                        </div>
                    ))}
                </div>
            )}

            {/* Content with typewriter */}
            {msg.role === 'assistant' ? (
                <div className="relative">
                    <div className="prose prose-invert max-w-none prose-response
                      prose-headings:text-zinc-50 prose-headings:font-bold prose-headings:tracking-tight
                      prose-h1:text-[1.35rem] prose-h1:leading-snug prose-h1:mb-4 prose-h1:mt-6
                      prose-h2:text-[1.2rem] prose-h2:leading-snug prose-h2:mb-3 prose-h2:mt-5
                      prose-h3:text-[1.05rem] prose-h3:leading-snug prose-h3:mb-2.5 prose-h3:mt-4
                      prose-p:text-[0.95rem] prose-p:text-zinc-200 prose-p:leading-[1.8] prose-p:mb-4 prose-p:font-normal
                      prose-strong:text-white prose-strong:font-bold
                      prose-em:text-zinc-300
                      prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline prose-a:font-medium
                      prose-code:text-emerald-300 prose-code:bg-zinc-800/70 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:text-[0.85rem] prose-code:font-medium prose-code:border prose-code:border-zinc-700/50
                      prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-800 prose-pre:rounded-xl prose-pre:p-4 prose-pre:my-4
                      prose-ul:text-zinc-200 prose-ul:my-3 prose-ul:text-[0.95rem]
                      prose-ol:text-zinc-200 prose-ol:my-3 prose-ol:text-[0.95rem]
                      prose-li:my-1.5 prose-li:leading-[1.75] prose-li:text-zinc-200
                      prose-hr:border-zinc-800 prose-hr:my-6
                      prose-blockquote:border-l-[3px] prose-blockquote:border-indigo-500/40 prose-blockquote:bg-indigo-500/5 prose-blockquote:px-4 prose-blockquote:py-2 prose-blockquote:rounded-r-lg prose-blockquote:text-zinc-300 prose-blockquote:text-[0.95rem]
                      prose-table:border-collapse prose-th:border prose-th:border-zinc-700 prose-th:bg-zinc-800/60 prose-th:px-3 prose-th:py-2.5 prose-th:text-zinc-100 prose-th:text-[0.8rem] prose-th:font-semibold prose-th:uppercase prose-th:tracking-wide
                      prose-td:border prose-td:border-zinc-800 prose-td:px-3 prose-td:py-2 prose-td:text-zinc-200 prose-td:text-[0.85rem]
                    ">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{textToRender}</ReactMarkdown>
                    </div>
                    {/* Blinking cursor while typing */}
                    {isTyping && <span className="typewriter-cursor" />}

                    {/* Click to skip typing */}
                    {isTyping && (
                        <button
                            onClick={skipToEnd}
                            className="absolute -bottom-1 right-0 text-[10px] text-zinc-600 hover:text-zinc-400 transition-colors flex items-center gap-1 opacity-60 hover:opacity-100"
                        >
                            <Zap size={10} />
                            Skip
                        </button>
                    )}
                </div>
            ) : (
                msg.content
            )}

            {/* Footer metadata — only visible after typing is done */}
            {msg.role === 'assistant' && !msg.isError && isDone && (msg.elapsed || msg.sourcesCount) && (
                <div className="footer-fade-in mt-5 pt-3 border-t border-zinc-800/50 flex flex-wrap items-center gap-4 text-[11px] text-zinc-500 font-medium tracking-wide">
                    {msg.elapsed && (
                        <span className="inline-flex items-center gap-1.5">
                            <Clock size={11} className="text-zinc-600" />
                            {msg.elapsed}s
                        </span>
                    )}
                    {msg.sourcesCount != null && msg.sourcesCount > 0 && (
                        <span className="inline-flex items-center gap-1.5">
                            <Database size={11} className="text-zinc-600" />
                            {msg.sourcesCount} sources
                        </span>
                    )}
                    {msg.symbols && msg.symbols.length > 0 && (
                        <span className="inline-flex items-center gap-1.5">
                            <TrendingUp size={11} className="text-zinc-600" />
                            {msg.symbols.join(', ')}
                        </span>
                    )}
                </div>
            )}
        </div>
    );
}

export default function ChatInterface({ isSidebarOpen, onToggleSidebar, messages, setMessages, ensureActiveSession }: ChatInterfaceProps) {
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isConnected, setIsConnected] = useState<boolean | null>(null);
    const [currentRoute, setCurrentRoute] = useState<string | null>(null);
    const [analysisMode, setAnalysisMode] = useState<AnalysisMode>('auto');
    const [engineVersion, setEngineVersion] = useState('');
    const [typingId, setTypingId] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom on new messages & during typing
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading, typingId]);

    // Scroll during typing animation  
    useEffect(() => {
        if (typingId !== null) {
            const scrollInterval = setInterval(() => {
                messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }, 150);
            return () => clearInterval(scrollInterval);
        }
    }, [typingId]);

    // Check backend health on mount
    useEffect(() => {
        const checkHealth = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/health`);
                if (res.ok) {
                    setIsConnected(true);
                    const data = await res.json();
                    setEngineVersion(data.engine || 'MarketMind');
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

        // Auto-create session if none exists
        ensureActiveSession();

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
                body: JSON.stringify({ query, mode: analysisMode }),
            });

            const data = await res.json();

            if (data.success !== false) {
                const msgTypingId = `typing-${Date.now()}`;
                const aiMsg: Message = {
                    role: 'assistant',
                    content: data.report,
                    route: data.route,
                    routeLabel: data.route_label,
                    routeEmoji: data.route_emoji,
                    mode: data.mode,
                    confidence: data.confidence,
                    confidenceReasons: data.confidence_reasons,
                    contradictions: data.contradictions,
                    isFollowUp: data.is_follow_up,
                    elapsed: data.elapsed,
                    sourcesCount: data.sources_count,
                    symbols: data.symbols,
                    typingId: msgTypingId,
                };
                setMessages(prev => [...prev, aiMsg]);
                setTimeout(() => setTypingId(msgTypingId), 0);
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
        // Auto-create session if none exists
        ensureActiveSession();

        const userMsg: Message = { role: 'user', content: '☀️ Morning Briefing' };
        setMessages(prev => [...prev, userMsg]);
        setIsLoading(true);

        try {
            const res = await fetch(`${API_BASE}/api/morning-briefing`);
            const data = await res.json();

            if (data.success) {
                const msgTypingId = `typing-${Date.now()}`;
                const aiMsg: Message = {
                    role: 'assistant',
                    content: data.report,
                    route: data.route,
                    routeLabel: data.route_label || 'Morning Briefing',
                    routeEmoji: data.route_emoji || '☀️',
                    confidence: data.confidence,
                    typingId: msgTypingId,
                };
                setMessages(prev => [...prev, aiMsg]);
                setTimeout(() => setTypingId(msgTypingId), 0);
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
        // Auto-create session if none exists
        ensureActiveSession();

        if (prompt === '/briefing') {
            fetchMorningBriefing();
        } else {
            setInput(prompt);
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
                        <span className="px-2 py-0.5 rounded-full bg-indigo-500/10 text-[10px] uppercase font-bold text-indigo-400 border border-indigo-500/20 tracking-wider">LangGraph</span>
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
                                    Your AI Financial Research Agent
                                </h2>
                                <p className="text-sm text-zinc-400 max-w-lg mx-auto leading-relaxed">
                                    Powered by <span className="text-indigo-400 font-medium">LangGraph</span> + <span className="text-zinc-200 font-medium">Gemini 2.5</span> + <span className="text-zinc-200 font-medium">Real-time Data</span>.
                                    Memory-aware research with confidence scoring.
                                </p>
                                {/* Feature badges */}
                                <div className="flex items-center justify-center gap-2 flex-wrap">
                                    <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-bold uppercase tracking-wider border border-emerald-500/20">⚡ Quick &lt;30s</span>
                                    <span className="px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 text-[10px] font-bold uppercase tracking-wider border border-indigo-500/20">🔬 Deep &lt;3min</span>
                                    <span className="px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 text-[10px] font-bold uppercase tracking-wider border border-amber-500/20">🧠 Memory</span>
                                    <span className="px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 text-[10px] font-bold uppercase tracking-wider border border-rose-500/20">⚠️ Contradictions</span>
                                </div>
                                {/* Coverage badges */}
                                <div className="flex items-center justify-center gap-2 flex-wrap">
                                    <span className="px-2.5 py-1 rounded-full bg-zinc-800 text-zinc-400 text-[10px] font-bold uppercase tracking-wider border border-zinc-700/50">Indian NSE</span>
                                    <span className="px-2.5 py-1 rounded-full bg-zinc-800 text-zinc-400 text-[10px] font-bold uppercase tracking-wider border border-zinc-700/50">US NYSE/NASDAQ</span>
                                    <span className="px-2.5 py-1 rounded-full bg-zinc-800 text-zinc-400 text-[10px] font-bold uppercase tracking-wider border border-zinc-700/50">Crypto</span>
                                    <span className="px-2.5 py-1 rounded-full bg-zinc-800 text-zinc-400 text-[10px] font-bold uppercase tracking-wider border border-zinc-700/50">Commodities</span>
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
                            
                        </div>
                    </div>
                ) : (
                    /* Messages List */
                    <div className="max-w-3xl mx-auto w-full p-4 md:p-6 space-y-8 pb-40">
                        {messages.map((msg, idx) => (
                            <div
                                key={msg.typingId || idx}
                                className={`flex w-full message-animate-in ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
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
                                    {msg.role === 'assistant' ? (
                                        <TypewriterMessage
                                            msg={msg}
                                            shouldAnimate={!!msg.typingId && msg.typingId === typingId}
                                            onTypingDone={() => {
                                                if (msg.typingId === typingId) {
                                                    setTypingId(null);
                                                }
                                            }}
                                        />
                                    ) : (
                                        msg.content
                                    )}
                                </div>
                            </div>
                        ))}

                        {isLoading && (
                            <div className="flex justify-start w-full px-4 py-10 mb-20 message-animate-in">
                            <div className="flex items-center gap-4">
                                {/* Soft, glowing icon container with a slow spin */}
                                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-50/80 to-purple-50/80 dark:from-indigo-500/10 dark:to-purple-500/10 border border-indigo-100 dark:border-indigo-500/20 flex items-center justify-center animate-[spin_4s_linear_infinite]">
                                    <Sparkles size={14} className="text-indigo-600 dark:text-indigo-400" />
                                </div>
                        
                                {/* Smooth pulsing text instead of blocky skeletons */}
                                <div className="flex items-center gap-2 animate-pulse duration-1000">
                                    <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                                        {analysisMode === 'deep' ? 'Deep analysis in progress...' : 'Thinking...'}
                                    </span>
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
                        {/* Mode Selector */}
                        <ModeSelector mode={analysisMode} onChange={setAnalysisMode} />

                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder={
                                analysisMode === 'deep'
                                    ? "Deep analysis — bull/bear thesis, investment memos..."
                                    : analysisMode === 'quick'
                                        ? "Quick lookup — prices, summaries, key data..."
                                        : "Ask about any stock, crypto, or market trend..."
                            }
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
                        MarketMind AI &middot; LangGraph Research Agent &middot; Quick ⚡ &amp; Deep 🔬 Modes
                    </div>
                </div>
            </div>

        </div>
    );
}
