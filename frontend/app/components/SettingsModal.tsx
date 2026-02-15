'use client';

import { useState, useEffect } from 'react';
import { X, Plus, Trash2, Save, AlertCircle } from 'lucide-react';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
    const [activeTab, setActiveTab] = useState<'portfolio' | 'profile'>('portfolio');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Data State
    const [stocks, setStocks] = useState<any[]>([]);
    const [profile, setProfile] = useState<any>({});

    // New Stock Input
    const [newSymbol, setNewSymbol] = useState('');
    const [newSector, setNewSector] = useState('');

    // Load data when modal opens
    useEffect(() => {
        if (isOpen) {
            setError(null);
            setIsLoading(true);
            fetch('http://localhost:5001/api/portfolio')
                .then(res => {
                    if (!res.ok) throw new Error('Failed to fetch data');
                    return res.json();
                })
                .then(data => {
                    setStocks(data.stocks || []);
                    setProfile(data.profile || {});
                })
                .catch(err => {
                    console.error("Settings fetch error:", err);
                    setError("Could not load portfolio. Ensure backend is running.");
                })
                .finally(() => setIsLoading(false));
        }
    }, [isOpen]);

    const handleAddStock = () => {
        if (!newSymbol || !newSector) return;
        setStocks([...stocks, { symbol: newSymbol.toUpperCase(), name: newSymbol.toUpperCase(), sector: newSector }]);
        setNewSymbol('');
        setNewSector('');
    };

    const handleRemoveStock = (index: number) => {
        const newStocks = [...stocks];
        newStocks.splice(index, 1);
        setStocks(newStocks);
    };

    const handleSave = async () => {
        setIsLoading(true);
        try {
            const payload = {
                stocks,
                sectors: Array.from(new Set(stocks.map(s => s.sector))), // Auto-generate sectors
                profile
            };

            const res = await fetch('http://localhost:5001/api/portfolio', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                onClose();
                // Optional: Trigger a refresh of the sidebar/ticker
                window.location.reload();
            } else {
                alert("Failed to save settings");
            }
        } catch (e) {
            console.error(e);
            alert("Error saving settings");
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-zinc-900 border border-zinc-800 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">

                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-zinc-800">
                    <h2 className="text-lg font-semibold text-white">Settings & Portfolio</h2>
                    <button onClick={onClose} className="p-2 hover:bg-zinc-800 rounded-lg transition-colors">
                        <X size={20} className="text-zinc-400" />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-zinc-800">
                    <button
                        onClick={() => setActiveTab('portfolio')}
                        className={`flex-1 py-3 text-sm font-medium transition-colors ${activeTab === 'portfolio' ? 'bg-zinc-800 text-white border-b-2 border-blue-500' : 'text-zinc-400 hover:text-white'}`}
                    >
                        Manage Stocks
                    </button>
                    <button
                        onClick={() => setActiveTab('profile')}
                        className={`flex-1 py-3 text-sm font-medium transition-colors ${activeTab === 'profile' ? 'bg-zinc-800 text-white border-b-2 border-blue-500' : 'text-zinc-400 hover:text-white'}`}
                    >
                        Risk Profile
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">

                    {error && (
                        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm flex items-center gap-2">
                            <AlertCircle size={16} />
                            {error}
                        </div>
                    )}

                    {activeTab === 'portfolio' ? (
                        <div className="space-y-6">
                            {/* Add New Stock */}
                            <div className="bg-zinc-950/50 p-4 rounded-xl border border-zinc-800 space-y-3">
                                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Add New Stock</label>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        placeholder="Symbol (e.g. RELIANCE)"
                                        value={newSymbol}
                                        onChange={e => setNewSymbol(e.target.value)}
                                        className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-blue-500 outline-none placeholder:text-zinc-600"
                                    />
                                    <input
                                        type="text"
                                        placeholder="Sector (e.g. Energy)"
                                        value={newSector}
                                        onChange={e => setNewSector(e.target.value)}
                                        className="w-1/3 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-blue-500 outline-none placeholder:text-zinc-600"
                                    />
                                    <button
                                        onClick={handleAddStock}
                                        disabled={!newSymbol || !newSector}
                                        className="bg-blue-600 hover:bg-blue-500 text-white p-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        <Plus size={20} />
                                    </button>
                                </div>
                            </div>

                            {/* Stock List */}
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Your Holdings ({stocks.length})</label>
                                {stocks.map((stock, i) => (
                                    <div key={i} className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg border border-zinc-800/50 group hover:border-zinc-700 transition-colors">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-full bg-zinc-700/50 flex items-center justify-center text-xs font-bold text-zinc-300">
                                                {stock.symbol[0]}
                                            </div>
                                            <div>
                                                <div className="text-sm font-medium text-white">{stock.symbol}</div>
                                                <div className="text-xs text-zinc-500">{stock.sector}</div>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => handleRemoveStock(i)}
                                            className="text-zinc-500 hover:text-red-400 p-2 rounded-lg hover:bg-red-500/10 transition-colors"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-1.5">Risk Tolerance</label>
                                    <select
                                        value={profile.risk_tolerance || 'moderate'}
                                        onChange={e => setProfile({ ...profile, risk_tolerance: e.target.value })}
                                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm text-white focus:ring-1 focus:ring-blue-500 outline-none"
                                    >
                                        <option value="conservative">Conservative (Low Risk)</option>
                                        <option value="moderate">Moderate (Balanced)</option>
                                        <option value="aggressive">Aggressive (High Growth)</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-1.5">Investment Horizon</label>
                                    <select
                                        value={profile.investment_horizon || 'long-term'}
                                        onChange={e => setProfile({ ...profile, investment_horizon: e.target.value })}
                                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm text-white focus:ring-1 focus:ring-blue-500 outline-none"
                                    >
                                        <option value="short-term">Short Term (&lt; 1 Year)</option>
                                        <option value="medium-term">Medium Term (1-3 Years)</option>
                                        <option value="long-term">Long Term (3+ Years)</option>
                                    </select>
                                </div>

                                <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl flex items-start gap-3">
                                    <AlertCircle size={18} className="text-blue-400 shrink-0 mt-0.5" />
                                    <div className="text-sm text-blue-200">
                                        Changing your profile will adjust how the AI analyzes news. Aggressive profiles will see more growth opportunities, while conservative ones prioritize stability.
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-zinc-800 bg-zinc-950/50 flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm text-zinc-400 hover:text-white transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={isLoading}
                        className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                    >
                        {isLoading ? 'Saving...' : (
                            <>
                                <Save size={16} />
                                Save Changes
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
