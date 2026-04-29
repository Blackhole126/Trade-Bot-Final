import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import { X, CheckCircle2, AlertCircle, Link2, RefreshCw } from 'lucide-react';
import { hftApiService } from '../../services/hftApiService';
import type { HftSettingsUpdate } from '../../types/hft';

interface SettingsFormData {
    mode: 'live';
    riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CUSTOM';
    maxAllocation: number | string;
    stopLossPct: number | string;
    targetPriceLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CUSTOM';
    targetPricePct: number | string;
    productType: 'CNC' | 'MIS'; // CNC = Delivery, MIS = Intraday
}

interface HftSettingsModalProps {
    settings: any;
    onSave: (settings: any) => Promise<void>;
    onRefresh?: () => Promise<void>;
    onClose: () => void;
}

const HftSettingsModal: React.FC<HftSettingsModalProps> = ({ settings, onSave, onRefresh, onClose }) => {
    const { theme } = useTheme();
    const { user } = useAuth();
    const isLight = theme === 'light';
    const isSpace = theme === 'space';

    const [formData, setFormData] = useState<SettingsFormData>({
        mode: 'live',
        riskLevel: 'MEDIUM',
        maxAllocation: 25,
        stopLossPct: 5,
        targetPriceLevel: 'MEDIUM',
        targetPricePct: 8,
        productType: 'CNC' // Default to CNC (Delivery)
    });
    const [loading, setLoading] = useState(false);
    const [dhanConfigured, setDhanConfigured] = useState<boolean | null>(null);
    const [dhanError, setDhanError] = useState<string | null>(null);

    // Per-user demat (link/refresh)
    const [dematLinked, setDematLinked] = useState(false);
    const [dematBroker, setDematBroker] = useState<string>('');
    const [dematMaskedId, setDematMaskedId] = useState<string | null>(null);
    const [dematLoading, setDematLoading] = useState(false);
    const [dematError, setDematError] = useState<string | null>(null);
    const [dematSuccess, setDematSuccess] = useState<string | null>(null);
    const [showDematLinkForm, setShowDematLinkForm] = useState(false);
    const [showDematRefreshForm, setShowDematRefreshForm] = useState(false);
    const [dematLinkForm, setDematLinkForm] = useState({ broker: 'dhan', clientId: '', accessToken: '' });
    const [dematRefreshToken, setDematRefreshToken] = useState('');

    useEffect(() => {
        if (settings) {
            setFormData({
                mode: 'live',
                riskLevel: settings.riskLevel || 'MEDIUM',
                maxAllocation: settings.maxAllocation ? (settings.maxAllocation * 100) : 25,
                stopLossPct: settings.stopLossPct || 5,
                targetPriceLevel: settings.targetPriceLevel || 'MEDIUM',
                targetPricePct: settings.targetPricePct ? (settings.targetPricePct * 100) : 8,
                productType: settings.productType || 'CNC' // Load product type from settings
            });
        }
    }, [settings]);

    useEffect(() => {
        let cancelled = false;
        hftApiService.getLiveStatus()
            .then((res) => {
                if (!cancelled) {
                    setDhanConfigured(res.dhan_configured ?? false);
                    setDhanError(res.dhan_error ?? null);
                }
            })
            .catch(() => { if (!cancelled) { setDhanConfigured(false); setDhanError(null); } });
        return () => { cancelled = true; };
    }, []);

    useEffect(() => {
        if (!user?.username) {
            setDematLinked(false);
            setDematBroker('');
            setDematMaskedId(null);
            return;
        }
        let cancelled = false;
        hftApiService.getDematStatus()
            .then((res) => {
                if (!cancelled) {
                    setDematLinked(res.linked ?? false);
                    setDematBroker(res.broker ?? '');
                    setDematMaskedId(res.client_id_masked ?? null);
                }
            })
            .catch(() => { if (!cancelled) { setDematLinked(false); setDematBroker(''); setDematMaskedId(null); } });
        return () => { cancelled = true; };
    }, [user?.username]);

    const handleInputChange = (field: keyof SettingsFormData, value: any) => {
        setFormData(prev => {
            const newData = {
                ...prev,
                [field]: value
            };

            // Auto-update stop loss and allocation based on risk level
            if (field === 'riskLevel') {
                if (value === 'CUSTOM') {
                    newData.stopLossPct = '';
                    newData.maxAllocation = '';
                    newData.targetPricePct = '';  // Clear target price for custom mode
                } else {
                    const riskSettings: Record<string, { stopLoss: number; allocation: number; targetProfit: number }> = {
                        'LOW': { stopLoss: 3, allocation: 15, targetProfit: 6 },    // 2:1 risk-reward (3% * 2 = 6%)
                        'MEDIUM': { stopLoss: 5, allocation: 25, targetProfit: 10 }, // 2:1 risk-reward (5% * 2 = 10%)
                        'HIGH': { stopLoss: 8, allocation: 35, targetProfit: 16 }    // 2:1 risk-reward (8% * 2 = 16%)
                    };

                    if (riskSettings[value]) {
                        newData.stopLossPct = riskSettings[value].stopLoss;
                        newData.maxAllocation = riskSettings[value].allocation;
                        newData.targetPricePct = riskSettings[value].targetProfit; // Also update target price!
                    }
                }
            }

            // Auto-update target price based on target price level
            if (field === 'targetPriceLevel') {
                if (value === 'CUSTOM') {
                    newData.targetPricePct = '';
                } else {
                    // Match backend presets: LOW=6%, MEDIUM=10%, HIGH=16%
                    const targetSettings: Record<string, number> = {
                        'LOW': 6,      // Changed from 4 to 6
                        'MEDIUM': 10,  // Changed from 8 to 10
                        'HIGH': 16     // Changed from 12 to 16
                    };

                    if (targetSettings[value]) {
                        newData.targetPricePct = targetSettings[value];
                    }
                }
            }

            return newData;
        });
    };

    const handleSave = async () => {
        setLoading(true);
        try {
            const maxAllocationNum = parseFloat(String(formData.maxAllocation)) || 0;
            const stopLossPctNum = parseFloat(String(formData.stopLossPct)) || 0;
            const targetPricePctNum = parseFloat(String(formData.targetPricePct)) || 0;

            // Validate custom mode
            if (formData.riskLevel === 'CUSTOM') {
                if (!formData.maxAllocation || !formData.stopLossPct || maxAllocationNum <= 0 || stopLossPctNum <= 0) {
                    alert('Please enter valid values for both Max Allocation (1-100) and Stop Loss Percentage (1-20) when using Custom risk level.');
                    setLoading(false);
                    return;
                }

                if (maxAllocationNum < 1 || maxAllocationNum > 100) {
                    alert('Max Allocation must be between 1 and 100.');
                    setLoading(false);
                    return;
                }

                if (stopLossPctNum < 1 || stopLossPctNum > 20) {
                    alert('Stop Loss Percentage must be between 1 and 20.');
                    setLoading(false);
                    return;
                }
            }

            if (formData.targetPriceLevel === 'CUSTOM') {
                if (!formData.targetPricePct || targetPricePctNum <= 0) {
                    alert('Please enter a valid value for Target Price Percentage when using Custom level.');
                    setLoading(false);
                    return;
                }

                if (targetPricePctNum < 1 || targetPricePctNum > 50) {
                    alert('Target Price Percentage must be between 1 and 50.');
                    setLoading(false);
                    return;
                }
            }

            const settingsToSave: any = {
                mode: formData.mode,
                riskLevel: formData.riskLevel,
                maxAllocation: maxAllocationNum / 100,
                stopLoss: stopLossPctNum / 100,  // ALWAYS send stop loss (fixed from conditional)
                targetPriceLevel: formData.targetPriceLevel,
                targetPricePct: targetPricePctNum / 100,  // ALWAYS send target price
                productType: formData.productType, // CNC (Delivery) or MIS (Intraday)
                use_risk_reward: true,  // Always enable risk-reward
                risk_reward_ratio: 2.0,  // Default 2:1 ratio
                max_trade_limit: 150  // Default trade limit
            };

            console.log('Saving settings:', settingsToSave);
            await onSave(settingsToSave);
        } catch (error) {
            console.error('Error saving settings:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
        if (e.target === e.currentTarget) {
            onClose();
        }
    };

    const handleSaveDematLink = async () => {
        if (!dematLinkForm.clientId.trim() || !dematLinkForm.accessToken.trim()) {
            setDematError('Client ID and Access Token are required.');
            return;
        }
        setDematLoading(true);
        setDematError(null);
        setDematSuccess(null);
        try {
            await hftApiService.saveDemat(dematLinkForm.broker, dematLinkForm.clientId.trim(), dematLinkForm.accessToken.trim());
            setDematLinked(true);
            setDematBroker(dematLinkForm.broker);
            setDematMaskedId(dematLinkForm.clientId.trim().slice(0, 4) + '***');
            setDematSuccess('Demat account linked.');
            setShowDematLinkForm(false);
            setDematLinkForm(prev => ({ ...prev, clientId: '', accessToken: '' }));
            // Trigger refresh in parent
            if (onRefresh) onRefresh();
        } catch (err: any) {
            setDematError(err?.response?.data?.detail || err?.message || 'Failed to save demat credentials.');
        } finally {
            setDematLoading(false);
        }
    };

    const handleRefreshDematToken = async () => {
        if (!dematRefreshToken.trim()) {
            setDematError('Enter the new access token.');
            return;
        }
        setDematLoading(true);
        setDematError(null);
        setDematSuccess(null);
        try {
            await hftApiService.refreshDematToken(dematRefreshToken.trim());
            setDematSuccess('Access token updated. Use it for the next 24h.');
            setShowDematRefreshForm(false);
            setDematRefreshToken('');
            // Trigger refresh in parent
            if (onRefresh) onRefresh();
        } catch (err: any) {
            setDematError(err?.response?.data?.detail || err?.message || 'Failed to update token.');
        } finally {
            setDematLoading(false);
        }
    };

    const modalBg = isLight ? 'bg-white' : isSpace ? 'bg-slate-800/95' : 'bg-slate-800';
    const modalBorder = isLight ? 'border-gray-200' : isSpace ? 'border-purple-900/30' : 'border-slate-700';
    const textPrimary = isLight ? 'text-gray-900' : 'text-white';
    const textMuted = isLight ? 'text-gray-600' : 'text-gray-400';
    const inputBg = isLight ? 'bg-white' : 'bg-slate-700';
    const inputBorder = isLight ? 'border-gray-300' : 'border-slate-600';
    const inputDisabledBg = isLight ? 'bg-gray-100' : 'bg-slate-800';
    const selectBg = isLight ? 'bg-white' : 'bg-slate-700';
    const selectText = isLight ? 'text-gray-900' : 'text-white';

    return (
        <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={handleOverlayClick}
        >
            <div
                className={`${modalBg} border ${modalBorder} rounded-xl w-full max-w-lg shadow-2xl max-h-[90vh] overflow-y-auto`}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className={`flex items-center justify-between p-6 border-b ${modalBorder}`}>
                    <h3 className={`text-xl font-bold ${textPrimary}`}>Settings</h3>
                    <button
                        onClick={onClose}
                        className={`p-2 rounded-lg transition-colors ${isLight
                            ? 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                            : 'text-gray-400 hover:bg-slate-700 hover:text-white'
                            }`}
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-6">
                    {/* Connection Status Section - Systematic Redesign */}
                    <div className={`p-4 rounded-xl border ${modalBorder} ${isSpace ? 'bg-slate-900/50' : 'bg-slate-50'} space-y-3`}>
                        <div className="flex items-center justify-between">
                            <label className={`text-sm font-bold flex items-center gap-2 ${textPrimary}`}>
                                <Link2 className="w-4 h-4 text-blue-500" /> Broker Connection
                            </label>
                            {dematLinked ? (
                                <span className="flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-green-500/20 text-green-500 border border-green-500/30">
                                    <CheckCircle2 className="w-3 h-3" /> Active
                                </span>
                            ) : (
                                <span className="flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-500 border border-amber-500/30">
                                    <AlertCircle className="w-3 h-3" /> Not Linked
                                </span>
                            )}
                        </div>

                        {!user?.username ? (
                            <p className={`text-xs ${textMuted}`}>Log in to securely link your Dhan account for live portfolio tracking and order execution.</p>
                        ) : (
                            <div className="space-y-3">
                                {dematError && (
                                    <div className="px-3 py-2 rounded-lg text-xs bg-red-500/10 text-red-500 border border-red-500/20 flex items-start gap-2">
                                        <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                                        <span>{dematError}</span>
                                    </div>
                                )}
                                {dematSuccess && (
                                    <div className="px-3 py-2 rounded-lg text-xs bg-green-500/10 text-green-500 border border-green-500/20 flex items-start gap-2">
                                        <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
                                        <span>{dematSuccess}</span>
                                    </div>
                                )}

                                {dematLinked ? (
                                    <div className={`flex items-center justify-between p-3 rounded-lg border ${inputBorder} ${inputBg}`}>
                                        <div className="flex flex-col gap-0.5">
                                            <span className={`text-[10px] uppercase tracking-wider font-bold ${textMuted}`}>Linked Account</span>
                                            <span className={`text-sm font-medium ${textPrimary}`}>
                                                {dematBroker?.toUpperCase() || 'DHAN'} • <span className="font-mono text-xs opacity-80">{dematMaskedId}</span>
                                            </span>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                type="button"
                                                onClick={() => { setShowDematRefreshForm(true); setShowDematLinkForm(false); setDematError(null); setDematSuccess(null); }}
                                                disabled={dematLoading}
                                                title="Refresh access token"
                                                className={`p-2 rounded-lg transition-all ${isLight ? 'bg-amber-50 text-amber-600 border border-amber-200 hover:bg-amber-100' : 'bg-amber-500/10 text-amber-500 border border-amber-500/20 hover:bg-amber-500/20'}`}
                                            >
                                                <RefreshCw className={`w-4 h-4 ${dematLoading && showDematRefreshForm ? 'animate-spin' : ''}`} />
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => { setShowDematLinkForm(true); setShowDematRefreshForm(false); setDematError(null); setDematSuccess(null); }}
                                                disabled={dematLoading}
                                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${isLight ? 'bg-slate-100 text-slate-700 hover:bg-slate-200' : 'bg-slate-700 text-slate-200 hover:bg-slate-600'}`}
                                            >
                                                Edit
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex flex-col gap-3">
                                        <div className={`p-3 rounded-lg border ${inputBorder} ${isLight ? 'bg-amber-50' : 'bg-amber-500/5'} border-dashed`}>
                                            <p className={`text-xs ${isLight ? 'text-amber-700' : 'text-amber-400/90'}`}>
                                                {dhanConfigured ? "Backend is ready. Link your individual Dhan account to start trading." : "Broker credentials are not configured yet."}
                                            </p>
                                        </div>
                                        {!showDematLinkForm && (
                                            <button
                                                type="button"
                                                onClick={() => { setShowDematLinkForm(true); setShowDematRefreshForm(false); setDematError(null); setDematSuccess(null); }}
                                                disabled={dematLoading}
                                                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-bold shadow-lg shadow-blue-600/20 transition-all flex items-center justify-center gap-2"
                                            >
                                                <Link2 className="w-4 h-4" /> Link Dhan Account
                                            </button>
                                        )}
                                    </div>
                                )}

                                {showDematLinkForm && (
                                    <div className={`mt-3 p-4 rounded-lg border ${inputBorder} ${inputBg} shadow-inner space-y-3`}>
                                        <div className="flex items-center gap-2 mb-1">
                                            <Link2 className="w-4 h-4 text-blue-500" />
                                            <span className="text-sm font-bold">Link Account</span>
                                        </div>
                                        <p className={`text-[11px] ${textMuted} leading-relaxed`}>Select broker and enter credentials. These are used only for your portfolio and individual order execution.</p>

                                        <div className="space-y-2">
                                            <select
                                                value={dematLinkForm.broker}
                                                onChange={(e) => setDematLinkForm(prev => ({ ...prev, broker: e.target.value }))}
                                                className={`w-full px-3 py-2 rounded-lg border ${selectBg} ${selectText} ${inputBorder} text-sm focus:ring-2 focus:ring-blue-500/20 outline-none`}
                                            >
                                                <option value="dhan">Dhan (Default)</option>
                                            </select>
                                            <input
                                                type="text"
                                                placeholder="Client ID (e.g. 1100...)"
                                                value={dematLinkForm.clientId}
                                                onChange={(e) => setDematLinkForm(prev => ({ ...prev, clientId: e.target.value }))}
                                                className={`w-full px-3 py-2 rounded-lg border ${inputBg} ${inputBorder} text-sm focus:ring-2 focus:ring-blue-500/20 outline-none`}
                                            />
                                            <input
                                                type="password"
                                                placeholder="v2 Access Token"
                                                value={dematLinkForm.accessToken}
                                                onChange={(e) => setDematLinkForm(prev => ({ ...prev, accessToken: e.target.value }))}
                                                className={`w-full px-3 py-2 rounded-lg border ${inputBg} ${inputBorder} text-sm focus:ring-2 focus:ring-blue-500/20 outline-none`}
                                            />
                                        </div>

                                        <div className="flex gap-2 pt-1">
                                            <button type="button" onClick={() => setShowDematLinkForm(false)} className={`flex-1 px-3 py-2 rounded-lg text-xs font-bold border ${inputBorder} ${textMuted} hover:bg-slate-100 dark:hover:bg-slate-800 transition-all`}>Cancel</button>
                                            <button type="button" onClick={handleSaveDematLink} disabled={dematLoading} className="flex-1 px-3 py-2 rounded-lg text-xs font-bold bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-all">{dematLoading ? 'Linking...' : 'Link Account'}</button>
                                        </div>
                                    </div>
                                )}

                                {showDematRefreshForm && (
                                    <div className={`mt-3 p-4 rounded-lg border ${inputBorder} ${inputBg} shadow-inner space-y-3`}>
                                        <div className="flex items-center gap-2 mb-1">
                                            <RefreshCw className="w-4 h-4 text-amber-500" />
                                            <span className="text-sm font-bold">Refresh Token</span>
                                        </div>
                                        <p className={`text-[11px] ${textMuted} leading-relaxed`}>Access tokens typically expire every 24 hours. Paste your new token from the broker dashboard below.</p>

                                        <input
                                            type="password"
                                            placeholder="Paste new Access Token..."
                                            value={dematRefreshToken}
                                            onChange={(e) => setDematRefreshToken(e.target.value)}
                                            className={`w-full px-3 py-2 rounded-lg border ${inputBg} ${inputBorder} text-sm focus:ring-2 focus:ring-amber-500/20 outline-none`}
                                        />

                                        <div className="flex gap-2 pt-1">
                                            <button type="button" onClick={() => setShowDematRefreshForm(false)} className={`flex-1 px-3 py-2 rounded-lg text-xs font-bold border ${inputBorder} ${textMuted} hover:bg-slate-100 dark:hover:bg-slate-800 transition-all`}>Cancel</button>
                                            <button type="button" onClick={handleRefreshDematToken} disabled={dematLoading} className="flex-1 px-3 py-2 rounded-lg text-xs font-bold bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50 transition-all">{dematLoading ? 'Updating...' : 'Update Token'}</button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Risk Level */}
                    <div>
                        <label className={`block text-sm font-semibold mb-2 ${textPrimary}`}>
                            Risk Level:
                        </label>
                        <select
                            value={formData.riskLevel}
                            onChange={(e) => handleInputChange('riskLevel', e.target.value)}
                            disabled={loading}
                            className={`w-full px-4 py-3 rounded-lg border-2 transition-colors ${selectBg} ${selectText} ${inputBorder} focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed`}
                            style={{
                                appearance: 'auto',
                                WebkitAppearance: 'menulist',
                                MozAppearance: 'menulist'
                            }}
                        >
                            <option value="LOW" className={selectText}>Low (3% stop-loss, 15% allocation)</option>
                            <option value="MEDIUM" className={selectText}>Medium (5% stop-loss, 25% allocation)</option>
                            <option value="HIGH" className={selectText}>High (8% stop-loss, 35% allocation)</option>
                            <option value="CUSTOM" className={selectText}>Custom (Set your own values)</option>
                        </select>
                    </div>

                    {/* Product Type - CNC vs MIS */}
                    <div className={`border-t pt-4 ${modalBorder}`}>
                        <label className={`block text-sm font-semibold mb-3 ${textPrimary}`}>
                            Trading Product Type:
                        </label>
                        <div className="grid grid-cols-2 gap-3">
                            {/* CNC (Delivery) */}
                            <button
                                type="button"
                                onClick={() => handleInputChange('productType', 'CNC')}
                                className={`px-4 py-3 rounded-lg border-2 transition-all font-medium ${formData.productType === 'CNC'
                                        ? 'bg-green-600 border-green-600 text-white shadow-lg scale-105'
                                        : `${selectBg} ${selectText} ${inputBorder} hover:border-green-500`
                                    }`}
                            >
                                <div className="flex flex-col items-center">
                                    <span className="text-lg font-bold">📦 CNC</span>
                                    <span className="text-xs mt-1 opacity-80">Delivery (Long-term)</span>
                                    <span className="text-xs mt-0.5 opacity-70">• No auto square-off</span>
                                    <span className="text-xs mt-0.5 opacity-70">• Hold for days/years</span>
                                    <span className="text-xs mt-0.5 opacity-70">• Higher margin required</span>
                                </div>
                            </button>

                            {/* MIS (Intraday) */}
                            <button
                                type="button"
                                onClick={() => handleInputChange('productType', 'MIS')}
                                className={`px-4 py-3 rounded-lg border-2 transition-all font-medium ${formData.productType === 'MIS'
                                        ? 'bg-orange-600 border-orange-600 text-white shadow-lg scale-105'
                                        : `${selectBg} ${selectText} ${inputBorder} hover:border-orange-500`
                                    }`}
                            >
                                <div className="flex flex-col items-center">
                                    <span className="text-lg font-bold">⚡ MIS</span>
                                    <span className="text-xs mt-1 opacity-80">Intraday (Short-term)</span>
                                    <span className="text-xs mt-0.5 opacity-70">• Auto square-off at 3:15 PM</span>
                                    <span className="text-xs mt-0.5 opacity-70">• Close same day</span>
                                    <span className="text-xs mt-0.5 opacity-70">• Lower margin (5x leverage)</span>
                                </div>
                            </button>
                        </div>

                        {/* Info box showing current selection impact */}
                        <div className={`mt-3 p-3 rounded-lg border-l-4 ${formData.productType === 'CNC'
                                ? 'bg-green-50 border-green-600'
                                : 'bg-orange-50 border-orange-600'
                            }`}>
                            <p className={`text-sm font-medium ${formData.productType === 'CNC' ? 'text-green-900' : 'text-orange-900'
                                }`}>
                                {formData.productType === 'CNC' ? (
                                    <>
                                        <strong>CNC (Cash & Carry):</strong> Positions are held in demat account.
                                        Suitable for long-term investing. No automatic square-off.
                                        Brokerage: ₹20 per executed order.
                                    </>
                                ) : (
                                    <>
                                        <strong>MIS (Margin Intraday Square-off):</strong>
                                        Positions automatically squared off at 3:15 PM.
                                        Suitable for short-term trading with 5x leverage.
                                        Brokerage: ₹20 per executed order.
                                    </>
                                )}
                            </p>
                        </div>
                    </div>

                    {/* Max Allocation */}
                    <div>
                        <label className={`block text-sm font-semibold mb-2 ${textPrimary}`}>
                            Max Allocation per Trade (%):
                        </label>
                        <input
                            type="number"
                            min="1"
                            max="100"
                            value={formData.maxAllocation}
                            placeholder={formData.riskLevel === 'CUSTOM' ? 'Enter percentage (1-100)' : ''}
                            onChange={(e) => handleInputChange('maxAllocation', e.target.value)}
                            disabled={loading || formData.riskLevel !== 'CUSTOM'}
                            className={`w-full px-4 py-3 rounded-lg border-2 transition-colors ${formData.riskLevel === 'CUSTOM' ? inputBg : inputDisabledBg
                                } ${selectText} ${inputBorder} focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed`}
                        />
                        {formData.riskLevel !== 'CUSTOM' && (
                            <p className={`text-xs mt-2 ${textMuted}`}>
                                Select "Custom" risk level to modify this value
                            </p>
                        )}
                    </div>

                    {/* Stop Loss */}
                    <div>
                        <label className={`block text-sm font-semibold mb-2 ${textPrimary}`}>
                            Stop Loss Percentage (%):
                        </label>
                        <input
                            type="number"
                            min="1"
                            max="20"
                            step="0.1"
                            value={formData.stopLossPct}
                            placeholder={formData.riskLevel === 'CUSTOM' ? 'Enter percentage (1-20)' : ''}
                            onChange={(e) => handleInputChange('stopLossPct', e.target.value)}
                            disabled={loading || formData.riskLevel !== 'CUSTOM'}
                            className={`w-full px-4 py-3 rounded-lg border-2 transition-colors ${formData.riskLevel === 'CUSTOM' ? inputBg : inputDisabledBg
                                } ${selectText} ${inputBorder} focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed`}
                        />
                        {formData.riskLevel !== 'CUSTOM' && (
                            <p className={`text-xs mt-2 ${textMuted}`}>
                                Select "Custom" risk level to modify this value
                            </p>
                        )}
                    </div>

                    {/* Target Price Level */}
                    <div className={`border-t pt-4 ${modalBorder}`}>
                        <label className={`block text-sm font-semibold mb-2 ${textPrimary}`}>
                            Target Price Level:
                        </label>
                        <select
                            value={formData.targetPriceLevel}
                            onChange={(e) => handleInputChange('targetPriceLevel', e.target.value)}
                            disabled={loading}
                            className={`w-full px-4 py-3 rounded-lg border-2 transition-colors ${selectBg} ${selectText} ${inputBorder} focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed`}
                            style={{
                                appearance: 'auto',
                                WebkitAppearance: 'menulist',
                                MozAppearance: 'menulist'
                            }}
                        >
                            <option value="LOW" className={selectText}>Low (4% target price)</option>
                            <option value="MEDIUM" className={selectText}>Medium (8% target price)</option>
                            <option value="HIGH" className={selectText}>High (12% target price)</option>
                            <option value="CUSTOM" className={selectText}>Custom (Set your own percentage)</option>
                        </select>
                    </div>

                    {/* Target Price Percentage */}
                    <div>
                        <label className={`block text-sm font-semibold mb-2 ${textPrimary}`}>
                            Target Price Percentage (%):
                        </label>
                        <input
                            type="number"
                            min="1"
                            max="50"
                            step="0.1"
                            value={formData.targetPricePct}
                            placeholder={formData.targetPriceLevel === 'CUSTOM' ? 'Enter percentage (1-50)' : ''}
                            onChange={(e) => handleInputChange('targetPricePct', e.target.value)}
                            disabled={loading || formData.targetPriceLevel !== 'CUSTOM'}
                            className={`w-full px-4 py-3 rounded-lg border-2 transition-colors ${formData.targetPriceLevel === 'CUSTOM' ? inputBg : inputDisabledBg
                                } ${selectText} ${inputBorder} focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed`}
                        />
                        {formData.targetPriceLevel !== 'CUSTOM' && (
                            <p className={`text-xs mt-2 ${textMuted}`}>
                                Select "Custom" target price level to modify this value
                            </p>
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className={`flex items-center justify-end gap-3 p-6 border-t ${modalBorder}`}>
                    <button
                        onClick={onClose}
                        disabled={loading}
                        className={`px-6 py-2.5 rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${isLight
                            ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            : 'bg-slate-700 text-gray-200 hover:bg-slate-600'
                            }`}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={loading}
                        className="px-6 py-2.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors"
                    >
                        {loading ? 'Saving...' : 'Save Settings'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default HftSettingsModal;
