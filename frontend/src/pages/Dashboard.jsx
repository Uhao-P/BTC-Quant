import { useEffect, useState } from 'react';
import axios from 'axios';
import { XAxis, YAxis, Tooltip, ResponsiveContainer, Area, AreaChart, Brush } from 'recharts';
import AssetSelector from '../components/AssetSelector';
import { formatChartTimestamp, formatUpdatedAt } from '../utils/dashboardFormat';

const DASHBOARD_TIMEFRAME = '1m';
const REFRESH_INTERVAL_MS = 10000;

export default function Dashboard() {
  const [symbol, setSymbol] = useState('BTC-USDT-SWAP');
  const [price, setPrice] = useState(null);
  const [signal, setSignal] = useState(null);
  const [klines, setKlines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [klRes, sigRes] = await Promise.all([
          axios.get(`/api/v1/data/klines?symbol=${encodeURIComponent(symbol)}&timeframe=${DASHBOARD_TIMEFRAME}&limit=200`),
          axios.get(`/api/v1/signals/latest?symbol=${encodeURIComponent(symbol)}`).catch(() => null),
        ]);

        const newestFirst = klRes.data.data || [];
        const chronological = [...newestFirst].reverse();
        setKlines(chronological);
        setPrice(newestFirst.length > 0 ? newestFirst[0].close : null);
        setSignal(sigRes?.data?.signal || null);
        setUpdatedAt(new Date());
        setError(null);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [symbol]);

  if (loading) return <div className="text-gray-400">加载中...</div>;
  if (error) return <div className="text-red-400">无法连接后端: {error}</div>;

  const chartData = klines.map((k) => ({
    time: formatChartTimestamp(k.timestamp),
    price: k.close,
    volume: k.volume,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{symbol} 仪表盘</h1>
          <div className="mt-1 text-xs text-gray-500">
            1 分钟行情 · 每 10 秒刷新{updatedAt ? ` · 最近更新 ${formatUpdatedAt(updatedAt)}` : ''}
          </div>
        </div>
        <AssetSelector value={symbol} onChange={setSymbol} />
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="最新价格" value={price ? `$${price.toLocaleString()}` : '--'} color="text-white" />
        <StatCard
          label="信号方向"
          value={signal?.direction === 'long' ? '做多' : signal?.direction === 'short' ? '做空' : '中性'}
          color={signal?.direction === 'long' ? 'text-green-400' : signal?.direction === 'short' ? 'text-red-400' : 'text-gray-400'}
        />
        <StatCard label="信号强度" value={signal?.strength ? `${(signal.strength * 100).toFixed(0)}%` : '--'} color="text-yellow-400" />
        <StatCard label="综合评分" value={signal?.score ?? '--'} color="text-blue-400" />
      </div>

      {/* Price Chart */}
      <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
        <h2 className="text-sm font-medium text-gray-400 mb-3">价格走势 (1m)</h2>
        <div className="mb-2 text-xs text-gray-500">拖动图表底部滑块可缩放时间范围</div>
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="time"
              minTickGap={42}
              tick={{ fill: '#6b7280', fontSize: 11 }}
            />
            <YAxis domain={['auto', 'auto']} tick={{ fill: '#6b7280', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: '#1a1a25', border: '1px solid #2e2e45', borderRadius: 8 }}
              labelStyle={{ color: '#9ca3af' }}
            />
            <Area type="monotone" dataKey="price" stroke="#f59e0b" fill="url(#colorPrice)" strokeWidth={2} />
            <Brush
              dataKey="time"
              height={28}
              stroke="#f59e0b"
              fill="#171722"
              travellerWidth={10}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Signal Details */}
      {signal && (
        <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
          <h2 className="text-sm font-medium text-gray-400 mb-3">信号详情</h2>
          <div className="space-y-2">
            {signal.reasons?.map((r, i) => (
              <div key={i} className="text-sm text-gray-300">• {r}</div>
            ))}
            <div className="mt-3 border-t border-dark-600 pt-3">
              <div className="grid grid-cols-3 gap-4 text-sm">
                {Object.entries(signal.indicators || {}).slice(0, 12).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-gray-500">{k}</span>
                    <span className="text-gray-200">{typeof v === 'number' ? v.toFixed(3) : v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }) {
  return (
    <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
    </div>
  );
}
