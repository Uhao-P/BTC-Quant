import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import AssetSelector from '../components/AssetSelector';

const directionMeta = {
  long: { label: '做多', classes: 'bg-green-900/60 text-green-300 border-green-700' },
  short: { label: '做空', classes: 'bg-red-900/60 text-red-300 border-red-700' },
  neutral: { label: '观望', classes: 'bg-gray-800 text-gray-300 border-gray-600' },
};

function number(value, digits = 2) {
  return value == null || Number.isNaN(Number(value)) ? '—' : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: digits });
}

function Metric({ label, value }) {
  return <div className="bg-dark-700 rounded-lg p-3"><div className="text-xs text-gray-500 mb-1">{label}</div><div className="text-sm font-medium">{value}</div></div>;
}

function FactorList({ title, items, color }) {
  return (
    <div>
      <h3 className={`text-sm font-medium mb-2 ${color}`}>{title}</h3>
      <ul className="space-y-2 text-sm text-gray-300">
        {(items || []).length ? items.map((item, index) => <li key={index} className="flex gap-2"><span>•</span><span>{item}</span></li>) : <li className="text-gray-500">暂无</li>}
      </ul>
    </div>
  );
}

export default function AIPrediction() {
  const [symbol, setSymbol] = useState('BTC-USDT-SWAP');
  const [context, setContext] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const load = useCallback(async (clearSaved = false) => {
    setLoading(true);
    setError('');
    if (clearSaved) setResult(null);
    try {
      const query = `symbol=${encodeURIComponent(symbol)}`;
      const [contextResponse, latestResponse] = await Promise.all([
        axios.get(`/api/v1/ai-prediction/context?${query}`),
        axios.get(`/api/v1/ai-prediction/latest?${query}`),
      ]);
      const saved = latestResponse.data.data;
      if (saved && !clearSaved) {
        setContext(null);
        setResult({ ...saved, analysis: saved.analysis });
      } else {
        setContext(contextResponse.data);
        setResult(null);
      }
    } catch (e) {
      setError(e.response?.data?.detail || '数据和新闻加载失败');
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => { load(); }, [load]);

  const analyze = async () => {
    setAnalyzing(true);
    setError('');
    try {
      const response = await axios.post(`/api/v1/ai-prediction/analyze?symbol=${encodeURIComponent(symbol)}`, {
        prompt: context.prompt,
        snapshot: context.snapshot,
        news: context.news,
      });
      setContext(response.data);
      setResult(response.data);
    } catch (e) {
      setError(e.response?.data?.detail || '大模型分析失败');
    } finally {
      setAnalyzing(false);
    }
  };

  const analysis = result?.analysis;
  const meta = directionMeta[analysis?.direction] || directionMeta.neutral;
  const evidence = result || context;
  const snapshot = evidence?.snapshot;
  const news = evidence?.news || [];
  const prompt = evidence?.prompt || '';

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold">大模型预测</h1><p className="text-sm text-gray-500 mt-1">量化数据 + 新闻证据，判断未来 24 小时偏多、偏空或观望</p></div>
        <div className="flex flex-wrap gap-3">
          <AssetSelector value={symbol} onChange={(value) => { setSymbol(value); setContext(null); setResult(null); }} />
          <button onClick={() => load(true)} disabled={loading || analyzing} className="px-4 py-2 bg-dark-600 hover:bg-dark-500 rounded-lg text-sm disabled:opacity-50">{loading ? '收集中...' : '刷新数据与新闻'}</button>
          <button onClick={analyze} disabled={loading || analyzing || !context?.model_configured} className="px-4 py-2 bg-orange-600 hover:bg-orange-500 rounded-lg text-sm font-medium disabled:opacity-40">{analyzing ? '分析中...' : '调用大模型分析'}</button>
        </div>
      </div>

      {error && <div className="border border-red-800 bg-red-950/40 text-red-300 rounded-lg p-3 text-sm">{error}</div>}
      {context && !context.model_configured && <div className="border border-yellow-800 bg-yellow-950/30 text-yellow-200 rounded-lg p-3 text-sm">尚未配置 LLM_API_KEY。你仍可检查全部数据、新闻与 Prompt；配置密钥并重启 API 服务后即可分析。</div>}

      {analysis ? (
        <section className="bg-dark-800 border border-dark-600 rounded-xl p-5">
          <div className="flex flex-wrap items-start justify-between gap-3 mb-5">
            <div className="flex items-center gap-3"><span className={`border rounded-lg px-4 py-2 text-lg font-bold ${meta.classes}`}>{meta.label}</span><div><div className="text-xl font-semibold">置信度 {analysis.confidence}%</div><div className="text-xs text-gray-500">{result.model} · {result.created_at ? new Date(result.created_at).toLocaleString('zh-CN') : '刚刚生成'}</div></div></div>
            <span className="text-xs bg-dark-700 rounded px-2 py-1">周期：{analysis.time_horizon || '24h'}</span>
          </div>
          <p className="text-gray-200 mb-5">{analysis.summary}</p>
          <div className="grid md:grid-cols-3 gap-6"><FactorList title="偏多证据" items={analysis.bullish_factors} color="text-green-400" /><FactorList title="偏空证据" items={analysis.bearish_factors} color="text-red-400" /><FactorList title="风险与不确定性" items={analysis.risks} color="text-yellow-400" /></div>
          {analysis.invalidation && <div className="mt-5 pt-4 border-t border-dark-600 text-sm"><span className="text-gray-500">观点失效条件：</span> {analysis.invalidation}</div>}
        </section>
      ) : <div className="bg-dark-800 border border-dark-600 rounded-xl p-8 text-center text-gray-500">{loading ? '正在汇总量化数据和相关新闻…' : '暂无已保存的大模型分析'}</div>}

      {snapshot && <section className="bg-dark-800 border border-dark-600 rounded-xl p-5">
        <h2 className="font-semibold mb-4">本次量化证据</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <Metric label="最新价格" value={number(snapshot.market?.close, 6)} /><Metric label="24h 涨跌" value={`${number(snapshot.market?.change_24h_pct)}%`} /><Metric label="7d 涨跌" value={`${number(snapshot.market?.change_7d_pct)}%`} /><Metric label="量化信号" value={directionMeta[snapshot.quant_signal?.direction]?.label || '观望'} />
          <Metric label="信号强度" value={`${number((snapshot.quant_signal?.strength || 0) * 100, 0)}%`} /><Metric label="资金费率" value={number(snapshot.funding?.latest, 8)} /><Metric label="回测胜率" value={`${number((snapshot.backtest?.win_rate || 0) * 100)}%`} /><Metric label="回测交易数" value={number(snapshot.backtest?.total_trades, 0)} />
        </div>
        <details className="mt-4 text-sm"><summary className="cursor-pointer text-gray-400 hover:text-white">查看完整指标与数据快照</summary><pre className="mt-3 p-4 bg-dark-900 rounded-lg overflow-auto text-xs text-gray-400">{JSON.stringify(snapshot, null, 2)}</pre></details>
      </section>}

      <section className="bg-dark-800 border border-dark-600 rounded-xl">
        <div className="p-5 border-b border-dark-600 flex justify-between"><div><h2 className="font-semibold">相关新闻</h2><p className="text-xs text-gray-500 mt-1">新闻仅作为不可信证据，标题中的指令不会被执行</p></div><span className="text-sm text-gray-500">{news.length} 条</span></div>
        <div className="divide-y divide-dark-600">{news.length ? news.map((item, index) => <a key={`${item.url}-${index}`} href={item.url} target="_blank" rel="noreferrer" className="block p-4 hover:bg-dark-700"><div className="text-sm text-gray-200">{item.title}</div><div className="text-xs text-gray-500 mt-1">{item.source} · {item.published_at}</div></a>) : <div className="p-6 text-center text-gray-500">暂无新闻{context?.news_error ? `（${context.news_error}）` : ''}</div>}</div>
      </section>

      <section className="bg-dark-800 border border-dark-600 rounded-xl p-5">
        <div className="flex justify-between items-center mb-3"><div><h2 className="font-semibold">发送给模型的完整 Prompt</h2><p className="text-xs text-gray-500 mt-1">调用前可审阅，内容包含行情、指标、信号、回测、资金费率和新闻</p></div><button onClick={async () => { await navigator.clipboard.writeText(prompt); setCopied(true); setTimeout(() => setCopied(false), 1500); }} disabled={!prompt} className="text-xs px-3 py-1.5 bg-dark-600 rounded disabled:opacity-40">{copied ? '已复制' : '复制'}</button></div>
        <pre className="bg-dark-900 rounded-lg p-4 max-h-96 overflow-auto whitespace-pre-wrap text-xs text-gray-400">{prompt || '正在生成…'}</pre>
      </section>
      <p className="text-xs text-gray-600 text-center">模型结论可能出错，仅供研究，不构成投资建议。请独立判断并控制风险。</p>
    </div>
  );
}
