# TradeApi 通达信与同花顺交易接口示例

A 股程序化交易接口多语言接入示例。通过 **通达信客户端接口** 或 **同花顺客户端接口**，将已手动登录的证券账户接入自己的交易程序，完成资金、持仓、委托、成交查询，以及买入、卖出、融资买入和撤单。

支持 HTTP、Python SDK 和 DLL 接入，提供 Python、C++、C#、Java、Node.js、Go 六种语言的示例。适用于策略程序接入、交易工具开发及接口集成验证。

> 本仓库公开调用示例与用户文档，**不包含 TradeApi 运行包、官方客户端、账户授权文件或内部实现**。不是通达信或同花顺官方发布的产品，也不提供收益承诺。交易功能以运行包、兼容客户端及账户权限为准。

## 免费试用与接入咨询

获取运行包、申请试用或咨询购买与接入，请联系 **[Telegram @tradeapi8](https://t.me/tradeapi8)**。

<a href="https://t.me/tradeapi8"><img src="assets/telegram-qr.png" width="240" alt="TradeApi Telegram 联系二维码 @tradeapi8"></a>

二维码是联系人入口，不是支付码。请勿在 GitHub Issue 中发送账户、密码、令牌、授权文件或完整账户日志。

## 产品选择

| 产品 | 登录与使用方式 | 接入方式 | 文档 |
| --- | --- | --- | --- |
| 通达信客户端接口 | 从接口运行包启动通达信，用户手动登录后调用 | HTTP、Python SDK、DLL | [通达信接口说明](docs/tdx-api.md) |
| 同花顺客户端接口 | 可先手动登录再启动接口；切换账户后需等待状态就绪 | HTTP、Python SDK、DLL | [同花顺接口说明](docs/ths-api.md) |

两套 API 均在本机运行，默认端口分别为 `18769` 和 `18768`。示例不代替用户登录，不接收券商登录密码，也不模拟鼠标键盘。

## 功能概览

| 功能 | 通达信 | 同花顺 |
| --- | :---: | :---: |
| 服务状态与登录状态 | ✓ | ✓ |
| 资金与持仓 | ✓ | ✓ |
| 当日委托与当日成交 | ✓ | ✓ |
| 可撤单列表 | ✓ | ✓ |
| 股东代码查询 | ✓ | — |
| 买入与卖出 | ✓ | ✓ |
| 融资买入 | ✓ | ✓ |
| 单合同号撤单 | ✓ | ✓ |
| 已提交动作结果读取 | ✓ | ✓ |

此表是示例覆盖范围，不代表所有账户均有对应业务权限。查询金额和价格保留为字符串；同花顺明细通常保留客户端原始字段。

## 快速开始

1. 获取完整运行包，按随包说明配置客户端并安装管理员提供的账户授权文件。
2. 启动 API，在官方客户端手动登录；保持 API 与客户端运行。
3. 在本仓库根目录打开 PowerShell，设置对应产品的本机连接信息。令牌只留在本机，不写进公开配置。
4. 选择一种语言运行示例。只传产品名时默认查询资金，不发送委托或撤单。

通达信运行包连接配置示例，将目录替换成自己的路径：

```powershell
$tdxRoot = 'D:\TradeApiTDX'
$tdxConfig = Get-Content "$tdxRoot\config\client.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$env:TRADEAPI_TDX_URL = "http://127.0.0.1:$($tdxConfig.listen_port)"
$env:TRADEAPI_TDX_TOKEN = (Get-Content "$tdxRoot\config\service-token.txt" -Raw).Trim()
python examples/python/demo.py tdx
```

同花顺运行包连接配置示例：

```powershell
$thsRoot = 'D:\TradeApiTHS'
$thsConfig = Get-Content "$thsRoot\runtime\client.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$env:TRADEAPI_THS_URL = "http://127.0.0.1:$($thsConfig.api_port)"
$env:TRADEAPI_THS_TOKEN = $thsConfig.token
python examples/python/demo.py ths
```

没有 Python？可直接选择下表任一语言，连接环境变量的设置方式相同。运行包 API 在 Windows 本机；语言示例的位数不受客户端位数限制，DLL 模式须选择与调用进程位数匹配的 DLL。

## 多语言示例

| 语言 | 调用方式 | 入口与构建说明 |
| --- | --- | --- |
| Python | 标准库 HTTP、运行包 SDK、ctypes DLL | [Python](examples/python/README.md) |
| C++ | WinHTTP、动态加载 DLL | [C++](examples/cpp/README.md) |
| C# | HttpClient、cdecl DLL | [C#](examples/csharp/README.md) |
| Java | HTTP，Maven 工程 | [Java](examples/java/README.md) |
| Node.js | 标准库 HTTP，无 npm 依赖 | [Node.js](examples/nodejs/README.md) |
| Go | 标准库 HTTP，无第三方 Go 依赖 | [Go](examples/go/README.md) |

各语言使用同一组命令和 [公开端点映射](config/api-contract.json)，选择 `tdx` 或 `ths` 即可。下面以 Python HTTP 示例演示，其他语言只需替换启动命令。

## 状态与查询示例

```powershell
python examples/python/demo.py tdx health
python examples/python/demo.py tdx status
python examples/python/demo.py tdx query funds
python examples/python/demo.py tdx query holdings
python examples/python/demo.py tdx query orders
python examples/python/demo.py tdx query trades
python examples/python/demo.py tdx query cancelable_orders
python examples/python/demo.py tdx query shareholders

python examples/python/demo.py ths status
python examples/python/demo.py ths query funds
python examples/python/demo.py ths query holdings
python examples/python/demo.py ths query orders
python examples/python/demo.py ths query trades
python examples/python/demo.py ths query cancelable_orders
```

示例的统一查询名 `holdings`、`trades`、`cancelable_orders` 会分别映射到同花顺 API 的 `positions`、`deals`、`cancelable`。**这只是示例命令统一，不会改写服务端返回字段。**

资金查询返回示例，数据为虚构并省略其他字段：

```json
{
  "ok": true,
  "result": {
    "schema": "tradeapi_tdx.query.v1",
    "category": "funds",
    "count": 1,
    "records": [{"balance": "10000.00", "available": "8000.00"}]
  }
}
```

## 买卖与融资买入示例

先将 `config` 中所需模板复制为 `*.local.json`，填入自己确认过的证券代码、价格、数量及账户类型。模板含不可交易的占位代码，不直接发送。价格使用十进制字符串，代码保留前导零。

通达信直接提交：

```powershell
Copy-Item config/tdx-buy.example.json config/tdx-buy.local.json
# 编辑本地文件；每笔新动作填写新的 request_id。
python examples/python/demo.py tdx order config/tdx-buy.local.json
# 上一行只输出待发送参数；确认当前账户与全部参数后，下面才发送一次真实委托。
python examples/python/demo.py tdx order config/tdx-buy.local.json --execute
```

卖出使用 [tdx-sell.example.json](config/tdx-sell.example.json)；融资买入使用 [tdx-finance-buy.example.json](config/tdx-finance-buy.example.json)，需已登录有对应权限的两融账户。它们同样使用 `order` 命令。

同花顺先预览，再提交：

```powershell
Copy-Item config/ths-buy.example.json config/ths-buy.local.json
# 编辑本地文件后只创建预览，不发送最终委托。
python examples/python/demo.py ths preview-order config/ths-buy.local.json
# 仅当 pending=true 时，等待约0.5秒再查同一个 preview_id；一次命令只查一次。
python examples/python/demo.py ths poll-order YOUR_PREVIEW_ID
# ready=true、pending=false且参数无误后，才提交一次真实委托。
python examples/python/demo.py ths submit-order YOUR_PREVIEW_ID --execute
```

卖出使用 [ths-sell.example.json](config/ths-sell.example.json)；融资买入使用 [ths-finance-buy.example.json](config/ths-finance-buy.example.json)。普通买入不能代替融资买入：后者需 `side=buy` 与 `credit_type=financing_buy`，并有相应两融权限。

`--execute` 是本示例程序防止误运行的开关，**不是 API 字段，也不是新增的二次确认参数**。自己的程序调用提交接口即表示发送，无需传 `confirmed` 等字段。示例不会自动轮询或提交。

## 撤单与结果读取

```powershell
# 通达信：复制、编辑撤单模板，填写当前账户确实要撤销的合同号和新的 request_id。
python examples/python/demo.py tdx cancel config/tdx-cancel.local.json --execute
python examples/python/demo.py tdx result YOUR_SAVED_REQUEST_ID

# 同花顺：先创建单合同号撤单预览，待ready=true后提交。
python examples/python/demo.py ths preview-cancel config/ths-cancel.local.json
python examples/python/demo.py ths poll-cancel YOUR_CANCEL_PREVIEW_ID
python examples/python/demo.py ths submit-cancel YOUR_CANCEL_PREVIEW_ID --execute
python examples/python/demo.py ths result YOUR_SAVED_ACTION_ID
```

撤单模板：[通达信](config/tdx-cancel.example.json)、[同花顺](config/ths-cancel.example.json)。当日委托、可撤列表可用来核对实际状态；不要仅凭合同号推断订单仍可撤。

`result` 只读取服务保存的动作结果，不会重新委托或撤单。同花顺该接口不是券商回单更新接口，API 重启后记录可能不保留；查不到不能认定没有申报。

## 交易结果处理

- HTTP 200、外层 `ok=true` 或示例退出码 0，都不代表券商已经受理，更不代表成交。
- `accepted=false` 表示明确拒绝；`accepted=null`、`pending=true` 或合同号为空表示需核对，不能猜合同号。
- 网络超时、断连、业务拒绝或结果未知时，保存请求 ID／预览 ID，核对官方客户端，不自动重发交易。
- 查询空数组不是调用失败；同花顺快照读取时间不等于券商更新时间，刷新触发成功也不保证新数据已返回。
- 不要在提交过程中切换账户，也不要把令牌或 API 端口开放到公网。

## 文档与工程结构

| 内容 | 链接 |
| --- | --- |
| 启动、配置与常见问题 | [快速接入](docs/quick-start.md) |
| 通达信 HTTP 参数与回包 | [通达信接口](docs/tdx-api.md) |
| 同花顺预览、提交与回包 | [同花顺接口](docs/ths-api.md) |
| SDK 与 DLL 使用要点 | [SDK 与 DLL](docs/sdk-dll.md) |
| 各语言源码 | [examples](examples/) |
| 本地模拟测试与 CI | [tests](tests/README.md) |
| 问题提交与贡献 | [贡献说明](CONTRIBUTING.md) |
| GitHub 简介与发布步骤 | [上传准备](docs/github-publish.md) |

## 许可

本仓库自行编写的调用示例按 [MIT 许可证](LICENSE) 提供，可参考和修改。该许可不包含 TradeApi 商业运行包、官方客户端及其商标，不提供或转授账户使用权限。第三方依赖见 [依赖说明](THIRD_PARTY_NOTICES.md)。

关键词：A股程序化交易、通达信交易接口、同花顺交易接口、Python量化交易、C++交易接口、C#交易接口、Java交易接口、HTTP交易接口、DLL交易接口。
