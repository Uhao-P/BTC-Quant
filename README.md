# BTC-Quant

面向 OKX USDT 永续合约的量化研究与可视化原型。项目采集市场数据、计算多因子信号、执行无未来函数的 K 线回测，并通过 Web 界面展示结果。

> 这是研究工具，不是自动交易系统，也不构成投资建议。任何策略都应在充足历史数据、样本外区间与不同市场状态中验证后再考虑实盘使用。

## 功能

- 支持 `BTC-USDT-SWAP`、`ETH-USDT-SWAP` 与 `DOGE-USDT-SWAP`
- 从 Binance/OKX 回填历史 K 线，仅永久保存 `1m` 原始行情，并按需聚合 `5m`、`15m`、`1h`、`4h`、`1d`
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

### Docker Compose（推荐）

启动 API、OKX 数据采集器和前端：

```bash
docker compose up -d --build
```

启动完成后访问 [http://127.0.0.1:3000](http://127.0.0.1:3000)，API 位于 `http://127.0.0.1:8700`。SQLite 数据保存在 Docker 命名卷 `btc-quant_btc_quant_data` 中，重建容器不会丢失。

Docker 默认使用 Binance USD-M 永续公共行情，以便在部分网络无法连接 OKX 时仍可正常运行。三个标的会统一映射到项目的 `*-USDT-SWAP` 命名。需要切换回 OKX 时：

```bash
export MARKET_DATA_PROVIDER=okx
docker compose up -d
```

如果当前网络访问 OKX 需要本机代理，请先设置容器可访问的代理地址（不要在容器中使用 `127.0.0.1`）：

```bash
export OKX_PROXY=http://host.docker.internal:7890
docker compose up -d --build
```

查看状态与日志：

```bash
docker compose ps
docker compose logs -f
```

停止服务：

```bash
docker compose down
```

如需同时删除已采集的数据卷，请明确执行 `docker compose down -v`。

### 本地开发

```bash
git clone https://github.com/Uhao-P/BTC-Quant.git
cd BTC-Quant
cp .env.example .env
make init
```

### 完整历史数据

推荐只永久保存一分钟原始行情。其他周期由 API 从一分钟行情实时聚合，不会重复占用磁盘。Docker 中启动三个币的完整历史回填：

```bash
docker compose --profile tools run -d --name btc-quant-history-backfill history-backfill
docker logs -f btc-quant-history-backfill
```

任务会先为 BTC、ETH、DOGE 各回填最近 7 天，保证仪表盘、信号和回测尽快可用，然后从本地最早记录继续向前回填到交易所上市边界。完整回填成功后，会自动删除旧版直接保存的 `5m`、`1h` 数据。日常采集器还会每天执行一次维护：同一根 K 线的同策略信号采用更新而非重复插入，信号默认保留 365 天，指标缓存默认保留 90 天。

任务被中断后，可从数据库中已有的最早一分钟继续：

```bash
docker start -a btc-quant-history-backfill
```

如果容器已经完成而需要重新创建，先执行 `docker rm btc-quant-history-backfill`，再执行上面的首次启动命令。删除回填容器不会删除命名卷中的行情数据。

查看数据库占用：

```bash
docker compose exec api du -h /app/storage/btc_quant.db
```

普通的定量回填仍然可用（例如 BTC 一分钟 K 线）：

```bash
make backfill ARGS="--symbol BTC-USDT-SWAP --timeframe 1m --bars 1000"
```

也可回填 ETH 或 DOGE：

```bash
make backfill ARGS="--symbol ETH-USDT-SWAP --timeframe 1m --bars 1000"
make backfill ARGS="--symbol DOGE-USDT-SWAP --timeframe 1m --bars 1000"
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

### 大模型预测

网页侧栏的「AI 预测」会汇总当前币种的价格变化、技术指标、量化信号、资金费率、近期信号、回测统计和相关新闻，并展示实际发送给模型的完整 Prompt。模型返回做多、做空或观望结论、置信度、多空证据、风险和观点失效条件；最近一次分析会保存到数据库，刷新页面不会丢失。

先在 `.env` 中配置模型（默认使用 OpenAI Responses API）：

```env
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-5.6-terra
LLM_API_STYLE=responses
LLM_REASONING_EFFORT=medium
```

也可接入兼容 Chat Completions 的服务，将 `LLM_BASE_URL` 改为对应地址，并设置 `LLM_API_STYLE=chat_completions`。修改后运行 `docker compose up -d --build api frontend`。

- `GET /api/v1/ai-prediction/context`：汇总证据、新闻并生成 Prompt，不调用模型
- `POST /api/v1/ai-prediction/analyze`：调用模型并持久化分析
- `GET /api/v1/ai-prediction/latest`：读取最近一次已保存分析

> 大模型输出仅供研究，不构成投资建议。
