import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Signals from './pages/Signals';
import Backtest from './pages/Backtest';
import DataPage from './pages/DataPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/data" element={<DataPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
