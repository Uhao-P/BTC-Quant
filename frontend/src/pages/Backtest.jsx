import { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import AssetSelector from '../components/AssetSelector';

export default function Backtest() {
  const [symbol, setSymbol] = useState('BTC-USDT-SWAP');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const runBacktest = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`/api/v1/backtest/run?symbol=${encodeURIComponent(symbol)}&limit=1000`);
      setResult(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">回测</h1>
        <div className="flex gap-3">
        <AssetSelector value={symbol} onChange={(value) => { setSymbol(value); setResult(null); }} />
        <button
          onClick={runBacktest}
          disabled={loading}
          className="px-4 py-2 bg-dark-600 hover:bg-dark-500 rounded-lg text-sm transition-colors disabled:opacity-50"
        >
          {loading ? '回测中...' : '运行多因子回测'}
        </button>
        </div>
      </div>

      {result && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
            <h2 className="text-sm font-medium text-gray-400 mb-3">交易统计</h2>
            <div className="space-y-3">
              <MetricRow label="总交易次数" value={result.result.total_trades} />
              <MetricRow label="胜率" value={`${(result.result.win_rate * 100).toFixed(1)}%`}
                color={result.result.win_rate > 0.5 ? 'text-green-400' : 'text-red-400'} />
              <MetricRow label="总收益率" value={`${result.result.total_pnl_pct.toFixed(2)}%`}
                color={result.result.total_pnl_pct > 0 ? 'text-green-400' : 'text-red-400'} />
              <MetricRow label="最大回撤" value={`${(result.result.max_drawdown * 100).toFixed(2)}%`} color="text-red-400" />
              <MetricRow label="夏普比率" value={result.result.sharpe.toFixed(2)}
                color={result.result.sharpe > 1 ? 'text-green-400' : result.result.sharpe > 0 ? 'text-yellow-400' : 'text-red-400'} />
              <MetricRow label="平均持仓K线数" value={result.result.avg_hold_bars.toFixed(1)} />
              <MetricRow label="最新净值" value={`$${result.result.latest_equity.toLocaleString()}`} />
            </div>
          </div>

          <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
            <h2 className="text-sm font-medium text-gray-400 mb-3">策略概览</h2>
            <div className="text-sm text-gray-300 space-y-2">
              <p><span className="text-gray-500">标的:</span> {result.symbol}</p>
              <p><span className="text-gray-500">周期:</span> {result.timeframe}</p>
              <p><span className="text-gray-500">K线数量:</span> {result.bars}</p>
              <p className="text-gray-500 mt-4">策略: {result.strategy}（含手续费、滑点与 ATR 风控）</p>
            </div>

            {/* Mini chart */}
            <div className="h-40 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={[
                  { name: '胜率', value: result.result.win_rate * 100 },
                  { name: '亏损率', value: (1 - result.result.win_rate) * 100 },
                ]}>
                  <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ background: '#1a1a25', border: '1px solid #2e2e45', borderRadius: 8 }}
                    labelStyle={{ color: '#9ca3af' }}
                  />
                  <Bar dataKey="value" fill="#22c55e" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {!result && (
        <div className="bg-dark-800 rounded-xl p-8 border border-dark-600 text-center text-gray-500">
          点击「运行回测」开始
        </div>
      )}
    </div>
  );
}

function MetricRow({ label, value, color = 'text-white' }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className={`font-medium ${color}`}>{value}</span>
    </div>
  );
}
