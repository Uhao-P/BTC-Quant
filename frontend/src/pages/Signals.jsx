import { useState, useEffect } from 'react';
import axios from 'axios';
import AssetSelector from '../components/AssetSelector';

export default function Signals() {
  const [symbol, setSymbol] = useState('BTC-USDT-SWAP');
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchHistory = async () => {
    try {
      const res = await axios.get(`/api/v1/signals/history?symbol=${encodeURIComponent(symbol)}&limit=50`);
      setSignals(res.data.data || []);
    } catch (e) {
      console.error(e);
    }
  };

  const generateSignal = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`/api/v1/signals/generate?symbol=${encodeURIComponent(symbol)}`);
      if (res.data.signal) {
        await fetchHistory();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 30000);
    return () => clearInterval(interval);
  }, [symbol]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">交易信号</h1>
        <div className="flex gap-3">
        <AssetSelector value={symbol} onChange={(value) => { setSymbol(value); setSignals([]); }} />
        <button
          onClick={generateSignal}
          disabled={loading}
          className="px-4 py-2 bg-dark-600 hover:bg-dark-500 rounded-lg text-sm transition-colors disabled:opacity-50"
        >
          {loading ? '生成中...' : '生成新信号'}
        </button>
        </div>
      </div>

      <div className="bg-dark-800 rounded-xl border border-dark-600">
        <div className="p-4 border-b border-dark-600 text-sm text-gray-400">
          市场状态多因子 v2 — 趋势、动量、波动率、量能、资金费率与 ATR 风控
        </div>
        <div className="divide-y divide-dark-600">
          {signals.length === 0 ? (
            <div className="p-8 text-center text-gray-500">点击「生成新信号」开始</div>
          ) : (
            signals.map((s, i) => (
              <div key={s.id ?? `${s.timestamp}-${i}`} className="p-4">
                <div className="flex items-center gap-3 mb-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    s.direction === 'long' ? 'bg-green-900 text-green-400' :
                    s.direction === 'short' ? 'bg-red-900 text-red-400' :
                    'bg-gray-800 text-gray-400'
                  }`}>
                    {s.direction === 'long' ? '做多' : s.direction === 'short' ? '做空' : '中性'}
                  </span>
                  <span className="text-sm text-gray-400">评分: {s.score}</span>
                  <span className="text-sm text-gray-400">强度: {(s.strength * 100).toFixed(0)}%</span>
                  {s.timestamp && <span className="text-xs text-gray-500">{new Date(s.timestamp).toLocaleString('zh-CN')}</span>}
                </div>
                <div className="flex flex-wrap gap-2">
                  {s.reasons?.map((r, j) => (
                    <span key={j} className="text-xs text-gray-400 bg-dark-700 px-2 py-0.5 rounded">
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
