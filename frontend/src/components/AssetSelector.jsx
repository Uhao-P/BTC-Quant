export const ASSETS = [
  { symbol: 'BTC-USDT-SWAP', label: 'BTC' },
  { symbol: 'ETH-USDT-SWAP', label: 'ETH' },
  { symbol: 'DOGE-USDT-SWAP', label: 'DOGE' },
];

export default function AssetSelector({ value, onChange }) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="bg-dark-700 border border-dark-500 rounded-lg px-3 py-2 text-sm text-gray-200"
      aria-label="选择交易标的"
    >
      {ASSETS.map((asset) => (
        <option key={asset.symbol} value={asset.symbol}>{asset.label} / USDT 永续</option>
      ))}
    </select>
  );
}
