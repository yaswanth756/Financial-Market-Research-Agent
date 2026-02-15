'use client';

import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface StockData {
    symbol: string;
    current_price: number;
    change_pct: number;
    yf_symbol: string;
}

const ITEMS = [
    { symbol: "NIFTY50", name: "NIFTY", price: 21980.50, change: 0.45 },
    { symbol: "SENSEX", name: "SENSEX", price: 72450.30, change: 0.38 },
    { symbol: "TCS", name: "TCS", price: 3980.20, change: -1.2 },
    { symbol: "INFY", name: "Infosys", price: 1650.10, change: -0.8 },
    { symbol: "RELIANCE", name: "Reliance", price: 2950.00, change: 1.5 },
    { symbol: "HDFCBANK", name: "HDFC Bank", price: 1420.50, change: 0.1 },
    { symbol: "ICICIBANK", name: "ICICI Bank", price: 1080.40, change: 2.1 },
];

export default function Ticker() {
    const [data, setData] = useState<any[]>(ITEMS);

    // In a real app, fetch from API
    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await fetch('http://localhost:5001/api/market-data');
                const json = await res.json();
                if (json.stocks) {
                    const items = Object.values(json.stocks).map((s: any) => ({
                        symbol: s.symbol,
                        name: s.name || s.symbol,
                        price: s.current_price || 0,
                        change: s.change_pct || 0
                    }));
                    // Add indices manually if not in portfolio
                    if (ITEMS[0] && !items.find((i: any) => i.symbol === "NIFTY50")) items.unshift(ITEMS[0]);

                    setData(items);
                }
            } catch (e) {
                console.error("Ticker fetch error", e);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 30000); // Update every 30s
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="w-full bg-zinc-950 border-b border-zinc-800/80 h-10 flex items-center overflow-hidden relative z-20">
            <div className="flex items-center gap-8 animate-ticker whitespace-nowrap px-4">
                {/* Duplicate the list for seamless scrolling effect */}
                {[...data, ...data].map((item, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs font-medium">
                        <span className="text-zinc-400">{item.symbol}</span>
                        <span className="text-zinc-200">₹{item.price.toLocaleString()}</span>
                        <div className={`flex items-center gap-0.5 ${item.change > 0 ? 'text-emerald-400' :
                            item.change < 0 ? 'text-red-400' : 'text-zinc-500'
                            }`}>
                            {item.change > 0 ? <TrendingUp size={12} /> :
                                item.change < 0 ? <TrendingDown size={12} /> :
                                    <Minus size={12} />}
                            {Math.abs(item.change).toFixed(2)}%
                        </div>
                    </div>
                ))}
            </div>

            {/* Fade effect on edges */}
            <div className="absolute left-0 top-0 bottom-0 w-12 bg-gradient-to-r from-zinc-950 to-transparent pointer-events-none" />
            <div className="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-zinc-950 to-transparent pointer-events-none" />

            <style jsx>{`
                @keyframes ticker {
                    0% { transform: translateX(0); }
                    100% { transform: translateX(-50%); }
                }
                .animate-ticker {
                    animation: ticker 40s linear infinite;
                }
                .animate-ticker:hover {
                    animation-play-state: paused;
                }
            `}</style>
        </div>
    );
}
