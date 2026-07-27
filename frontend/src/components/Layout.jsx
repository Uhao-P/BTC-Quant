import { NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { path: '/', label: '仪表盘', icon: '📊' },
  { path: '/signals', label: '交易信号', icon: '⚡' },
  { path: '/backtest', label: '回测', icon: '📈' },
  { path: '/data', label: '数据', icon: '📁' },
];

export default function Layout() {
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <nav className="w-56 bg-dark-800 border-r border-dark-600 p-4 flex flex-col">
        <div className="text-xl font-bold mb-8 px-3">
          <span className="text-orange-400">BTC</span>
          <span className="text-gray-300">-Quant</span>
        </div>
        <div className="space-y-1 flex-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-dark-600 text-white font-medium'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-dark-700'
                }`
              }
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
        <div className="text-xs text-gray-500 px-3">v0.1.0 · OKX</div>
      </nav>

      {/* Main */}
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
