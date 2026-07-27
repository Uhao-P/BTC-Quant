# BTC-Quant

面向 OKX USDT 永续合约的量化研究与可视化原型。项目采集市场数据、计算多因子信号、执行无未来函数的 K 线回测，并通过 Web 界面展示结果。

> 这是研究工具，不是自动交易系统，也不构成投资建议。任何策略都应在充足历史数据、样本外区间与不同市场状态中验证后再考虑实盘使用。

## 功能

- 支持 `BTC-USDT-SWAP`、`ETH-USDT-SWAP` 与 `DOGE-USDT-SWAP`
- 从 OKX 回填历史 K 线，并定时采集 `1m`、`5m`、`1h` K 线和资金费率
- RSI、MACD、布林带、EMA、ATR 等技术指标
- 市场状态多因子策略：趋势、动量、RSI、成交量、资金费率拥挤度与 ATR 风控
- 线性永续合约回测：多空、反向开仓、手续费、滑点、止盈止损、净值、回撤与夏普比率
- FastAPI 后端和 React/Vite 仪表盘

## 架构

```text
OKX REST / WebSocket
        │
        ▼
  数据采集与历史回填
        │
        ▼
     SQLite 数据库
        │
        ├──► 技术指标 / 多因子信号 ──► FastAPI ──► React 仪表盘
        │
        └──► K 线回测引擎
```

## 环境要求

- Python 3.9+
- Node.js 18+
- pnpm 8+

## 快速开始

```bash
git clone https://github.com/Uhao-P/BTC-Quant.git
cd BTC-Quant
cp .env.example .env
make init
```

回填历史数据（例如 BTC 1 小时 K 线）：

```bash
make backfill ARGS="--symbol BTC-USDT-SWAP --timeframe 1h --bars 1000"
```

也可回填 ETH 或 DOGE：

```bash
make backfill ARGS="--symbol ETH-USDT-SWAP --timeframe 1h --bars 1000"
make backfill ARGS="--symbol DOGE-USDT-SWAP --timeframe 1h --bars 1000"
```

启动后端：

```bash
make run-api
```

另开一个终端启动前端：

```bash
cd frontend
pnpm dev
```

访问 [http://localhost:3000](http://localhost:3000)。

如需持续采集数据：

```bash
make run-collector
```

## 配置

在 `.env` 中配置数据库、代理和服务地址。默认使用本地 SQLite：

```dotenv
DATABASE_URL=sqlite:///./data/btc_quant.db
OKX_PROXY=
API_HOST=127.0.0.1
API_PORT=8700
```

公开市场数据不需要 OKX API 密钥；只有后续接入私有账户接口时才需要填写密钥相关变量。

## 策略与回测说明

`regime_multi_factor_v2` 在每根已完成 K 线后，根据下列信号评分：

- EMA 9 / 21 / 50 排列和 EMA21 斜率判断市场趋势
- MACD 判断动量方向
- RSI 过滤弱势、过热和极端状态
- 成交量相对 20 根均值确认价格变化
- 资金费率作为反拥挤修正因子
- ATR 设置 2 倍 ATR 止损和 3 倍 ATR 止盈

回测使用前序已完成的 K 线生成信号，并在下一根 K 线开盘价成交；模拟 taker 手续费、滑点、反向开仓以及止盈止损。夏普年化因子会根据 K 线周期调整。

策略评分与回测表现只用于研究，不能证明未来收益或“准确率”。建议至少进行样本外回测、滚动走步验证与交易成本敏感性分析。

## API

服务默认运行于 `http://127.0.0.1:8700`。

| 接口 | 用途 |
| --- | --- |
| `GET /health` | 健康检查 |
| `GET /api/v1/data/assets` | 支持的交易标的 |
| `GET /api/v1/data/klines` | K 线数据 |
| `GET /api/v1/data/funding` | 资金费率 |
| `GET /api/v1/indicators/latest` | 最新技术指标 |
| `GET /api/v1/signals/latest` | 最新多因子信号 |
| `GET /api/v1/backtest/run` | 运行回测 |

示例：

```bash
curl 'http://127.0.0.1:8700/api/v1/signals/latest?symbol=ETH-USDT-SWAP&timeframe=1h'
curl 'http://127.0.0.1:8700/api/v1/backtest/run?symbol=DOGE-USDT-SWAP&timeframe=1h&limit=1000'
```

## 测试

```bash
./venv/bin/python -m pytest -q
cd frontend && pnpm build
```

测试覆盖多因子信号、横盘 RSI、回测的开平仓/反向/滑点/手续费/止盈止损，以及三种标的的 API 接口可用性。

## 项目结构

```text
backend/       FastAPI 路由与应用入口
config/        环境和运行配置
data/          OKX 采集器、SQLAlchemy 模型与存储层
indicators/    技术指标和资金费率分析
strategies/    多因子信号与回测引擎
scripts/       初始化、历史回填与定时采集脚本
frontend/      React/Vite Web 界面
tests/         自动化测试
```

## 许可与风险

本仓库当前未附带开源许可证。加密资产及杠杆交易风险很高，请自行承担使用本项目及其输出的全部风险。
