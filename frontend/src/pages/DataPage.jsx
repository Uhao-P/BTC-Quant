import { useState, useEffect } from 'react';
import axios from 'axios';
import AssetSelector from '../components/AssetSelector';

export default function DataPage() {
  const [symbol, setSymbol] = useState('BTC-USDT-SWAP');
  const [klines, setKlines] = useState([]);
  const [funding, setFunding] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('klines');

  useEffect(() => {
    const fetch = async () => {
      try {
        const [klRes, frRes] = await Promise.all([
          axios.get(`/api/v1/data/klines?symbol=${encodeURIComponent(symbol)}&limit=100`),
          axios.get(`/api/v1/data/funding?symbol=${encodeURIComponent(symbol)}&limit=20`),
        ]);
        setKlines(klRes.data.data || []);
        setFunding(frRes.data.data || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [symbol]);

  const formatTime = (ts) => new Date(ts).toLocaleString('zh-CN');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">数据浏览器</h1>
        <AssetSelector value={symbol} onChange={setSymbol} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-dark-800 rounded-lg p-1 w-fit border border-dark-600">
        <button
          onClick={() => setTab('klines')}
          className={`px-4 py-2 rounded-md text-sm transition-colors ${
            tab === 'klines' ? 'bg-dark-600 text-white' : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          K 线数据
        </button>
        <button
          onClick={() => setTab('funding')}
          className={`px-4 py-2 rounded-md text-sm transition-colors ${
            tab === 'funding' ? 'bg-dark-600 text-white' : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          资金费率
        </button>
      </div>

      {/* Kline Table */}
      {tab === 'klines' && (
        <div className="bg-dark-800 rounded-xl border border-dark-600 overflow-hidden">
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-dark-700">
                <tr className="text-gray-400">
                  <th className="text-left p-3">时间</th>
                  <th className="text-right p-3">开盘</th>
                  <th className="text-right p-3">最高</th>
                  <th className="text-right p-3">最低</th>
                  <th className="text-right p-3">收盘</th>
                  <th className="text-right p-3">成交量</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-600">
                {klines.map((k, i) => (
                  <tr key={i} className="hover:bg-dark-700">
                    <td className="p-3 text-gray-400">{formatTime(k.timestamp)}</td>
                    <td className={`p-3 text-right ${k.open >= k.close ? 'text-red-400' : 'text-green-400'}`}>
                      {k.open.toFixed(2)}
                    </td>
                    <td className="p-3 text-right text-gray-200">{k.high.toFixed(2)}</td>
                    <td className="p-3 text-right text-gray-200">{k.low.toFixed(2)}</td>
                    <td className={`p-3 text-right font-medium ${k.close >= k.open ? 'text-green-400' : 'text-red-400'}`}>
                      {k.close.toFixed(2)}
                    </td>
                    <td className="p-3 text-right text-gray-400">{k.volume?.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Funding Table */}
      {tab === 'funding' && (
        <div className="bg-dark-800 rounded-xl border border-dark-600 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-dark-700">
                <tr className="text-gray-400">
                  <th className="text-left p-3">时间</th>
                  <th className="text-right p-3">资金费率</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-600">
                {funding.map((f, i) => (
                  <tr key={i} className="hover:bg-dark-700">
                    <td className="p-3 text-gray-400">{formatTime(f.timestamp)}</td>
                    <td className={`p-3 text-right font-medium ${
                      f.funding_rate > 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {(f.funding_rate * 100).toFixed(4)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
