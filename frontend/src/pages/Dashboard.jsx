import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { XAxis, YAxis, Tooltip, ResponsiveContainer, Area, AreaChart, Brush, Line, LineChart } from 'recharts';
import AssetSelector from '../components/AssetSelector';
import { formatHistoryTimestamp, formatUpdatedAt } from '../utils/dashboardFormat';

const DASHBOARD_TIMEFRAME = '1m';
const REFRESH_INTERVAL_MS = 10000;
const HISTORY_REFRESH_INTERVAL_MS = 60000;

function mergeLatestPoint(points, candle) {
  if (!candle) return points;
  const point = { timestamp: candle.timestamp, close: candle.close };
  const withoutSameTimestamp = points.filter((item) => item.timestamp !== point.timestamp);
  return [...withoutSameTimestamp, point].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

export default function Dashboard() {
  const [symbol, setSymbol] = useState('BTC-USDT-SWAP');
  const [price, setPrice] = useState(null);
  const [signal, setSignal] = useState(null);
  const [overviewData, setOverviewData] = useState([]);
  const [detailData, setDetailData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [historyRange, setHistoryRange] = useState(null);
  const selectedRangeRef = useRef(null);
  const detailRequestRef = useRef(0);
  const brushTimerRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const fetchLiveData = async () => {
      try {
        const [klRes, sigRes] = await Promise.all([
          axios.get(`/api/v1/data/klines?symbol=${encodeURIComponent(symbol)}&timeframe=${DASHBOARD_TIMEFRAME}&limit=1`, { signal: controller.signal }),
          axios.get(`/api/v1/signals/latest?symbol=${encodeURIComponent(symbol)}`, { signal: controller.signal }).catch(() => null),
        ]);

        if (!active) return;
        const newestFirst = klRes.data.data || [];
        const latest = newestFirst[0] || null;
        setPrice(latest?.close ?? null);
        setOverviewData((points) => mergeLatestPoint(points, latest));
        setDetailData((points) => selectedRangeRef.current ? points : mergeLatestPoint(points, latest));
        setSignal(sigRes?.data?.signal || null);
        setUpdatedAt(new Date());
        setError(null);
      } catch (e) {
        if (!axios.isCancel(e)) setError(e.message);
      }
    };

    const fetchHistory = async () => {
      try {
        const res = await axios.get(
          `/api/v1/data/price-history?symbol=${encodeURIComponent(symbol)}&max_points=2500`,
          { signal: controller.signal },
        );
        if (!active) return;
        const points = res.data.data || [];
        setOverviewData(points);
        if (!selectedRangeRef.current) setDetailData(points);
        setHistoryRange(res.data);
        setError(null);
      } catch (e) {
        if (!axios.isCancel(e)) setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    setLoading(true);
    detailRequestRef.current += 1;
    setOverviewData([]);
    setDetailData([]);
    setHistoryRange(null);
    selectedRangeRef.current = null;
    Promise.all([fetchLiveData(), fetchHistory()]);
    const liveInterval = setInterval(fetchLiveData, REFRESH_INTERVAL_MS);
    const historyInterval = setInterval(fetchHistory, HISTORY_REFRESH_INTERVAL_MS);
    return () => {
      active = false;
      controller.abort();
      clearInterval(liveInterval);
      clearInterval(historyInterval);
      clearTimeout(brushTimerRef.current);
    };
  }, [symbol]);

  const handleBrushChange = (range) => {
    if (!range || !overviewData.length) return;
    clearTimeout(brushTimerRef.current);
    brushTimerRef.current = setTimeout(async () => {
      const startPoint = overviewData[range.startIndex];
      const endPoint = overviewData[range.endIndex];
      if (!startPoint || !endPoint) return;
      if (range.startIndex === 0 && range.endIndex === overviewData.length - 1) {
        selectedRangeRef.current = null;
        setDetailData(overviewData);
        return;
      }
      const selection = { start: startPoint.timestamp, end: endPoint.timestamp };
      selectedRangeRef.current = selection;
      const requestId = ++detailRequestRef.current;
      try {
        const params = new URLSearchParams({
          symbol,
          max_points: '2500',
          start: selection.start,
          end: selection.end,
        });
        const res = await axios.get(`/api/v1/data/price-history?${params}`);
        if (requestId === detailRequestRef.current) setDetailData(res.data.data || []);
      } catch (e) {
        if (requestId === detailRequestRef.current) setError(e.message);
      }
    }, 250);
  };

  if (loading) return <div className="text-gray-400">加载中...</div>;
  if (error) return <div className="text-red-400">无法连接后端: {error}</div>;

  const chartData = detailData.map((k) => ({
    timestamp: k.timestamp,
    price: k.close,
  }));
  const navigatorData = overviewData.map((k) => ({ timestamp: k.timestamp, price: k.close }));

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
        <h2 className="text-sm font-medium text-gray-400 mb-1">全部历史价格走势</h2>
        <div className="mb-2 text-xs text-gray-500">
          拖动底部导航条选择任意历史区间；缩小范围后自动加载分钟级明细
          {historyRange?.oldest && historyRange?.latest
            ? ` · ${formatHistoryTimestamp(historyRange.oldest)} 至 ${formatHistoryTimestamp(historyRange.latest)} · ${historyRange.source_count.toLocaleString()} 根分钟线`
            : ''}
        </div>
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="timestamp"
              minTickGap={42}
              tickFormatter={formatHistoryTimestamp}
              tick={{ fill: '#6b7280', fontSize: 11 }}
            />
            <YAxis domain={['auto', 'auto']} tick={{ fill: '#6b7280', fontSize: 11 }} />
            <Tooltip
              labelFormatter={formatHistoryTimestamp}
              contentStyle={{ background: '#1a1a25', border: '1px solid #2e2e45', borderRadius: 8 }}
              labelStyle={{ color: '#9ca3af' }}
            />
            <Area type="monotone" dataKey="price" stroke="#f59e0b" fill="url(#colorPrice)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
        <ResponsiveContainer width="100%" height={90}>
          <LineChart data={navigatorData}>
            <Line type="monotone" dataKey="price" stroke="#6b7280" dot={false} strokeWidth={1} />
            <Brush
              dataKey="timestamp"
              height={32}
              stroke="#f59e0b"
              fill="#171722"
              travellerWidth={12}
              tickFormatter={formatHistoryTimestamp}
              onChange={handleBrushChange}
            />
          </LineChart>
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
