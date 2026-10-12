# 同花顺客户端接口

默认地址 `http://127.0.0.1:18768`。除 `GET /health` 外，请求头包含 `Authorization: Bearer <本机token>`。POST 使用UTF-8 JSON对象。

## 查询

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/health` | 服务存活 |
| GET | `/session/status` | 登录状态，检查状态中的loggedIn |
| GET | `/query/funds` | 资金 |
| GET | `/query/positions` | 持仓 |
| GET | `/query/orders` | 当日委托 |
| GET | `/query/deals` | 当日成交 |
| GET | `/query/cancelable` | 可撤单列表，仅查询 |

结果通常位于 `result.data.records`。资金可见 `kyje` 可用、`zzc` 总资产、`zsz` 市值；持仓可见 `zqdm` 代码、`zqmc` 名称；合同号通常为 `htbh`。不同客户端或券商明细字段可能不同，按实际JSON读取。

资金和持仓会尝试触发刷新后读取客户端快照；`refresh.requested=true` 不等于券商最新数据已经返回。`retrieved_at_ms` 是本机读取时间，不是行情或券商更新时间。

## 委托预览

`POST /orders/preview` 准备参数，不发送最终委托。

```json
{"side":"buy","security_code":"600000","price":"10.00","quantity":100}
```

以上仅为格式示例。方向buy或sell，证券代码为六位字符串，价格正数文本、最多四位小数，数量为正整数。数量和权限还须满足实际证券规则。

两融可增加credit_type：买入方向为collateral_buy、financing_buy、buy_to_repay；卖出方向为collateral_sell、short_sell、sell_to_repay。融资买入用 `side=buy, credit_type=financing_buy`。普通账户不传该字段；两融不传时不能当作融资买入。

预览回包示例，省略其他字段：

```json
{"ok":true,"result":{"preview_id":"preview_example_id","ready":true,"pending":false,"expires_at":2000000000}}
```

如果pending=true，等待约0.5秒后向同一个 `/orders/preview` 发送 `{"preview_id":"preview_example_id"}`，只检查准备状态，不是重复下单。期限以expires_at为准；ready=true、pending=false后才提交。示例一次命令只检查一次，失败、过期或账户切换时停止。

## 真实委托提交

`POST /orders/submit`，仅传 `{"preview_id":"preview_example_id"}`。主动调用表示真实发送，无需confirmed字段。每个预览只提交一次，不自动重试。

即时响应可能没有合同号：

```json
{
  "ok": true,
  "result": {
    "action_id": "preview_example_id",
    "order_id": null,
    "accepted": null,
    "pending": true,
    "status": "untracked",
    "automatic_retry": false
  }
}
```

HTTP200及外层ok不等于券商受理。合同号为空、pending或untracked时核对客户端，不猜测合同号或重新提交。

## 撤单

1. `POST /cancels/preview`，正文 `{"order_id":"123456"}`，准备指定合同号撤单。
2. 若未就绪，等待后向相同地址发送 `{"preview_id":"cancel_example_id"}` 检查一次。
3. ready=true、pending=false后，`POST /cancels/submit` 传相同preview_id，发送一次真实撤单。

只支持单合同号撤单。预览不是撤销成功，也不保证提交时订单仍可撤。

## 已提交结果与错误

`GET /actions/<action_id>` 只读取保存的原提交结果，不向券商更新回单，不补齐缺失合同号。action_id通常就是preview_id。API重启后记录不保留；查不到也不能当作未发送。

错误通常为 `{"ok":false,"error":"错误说明","type":"错误类别"}`。所有错误和未知状态都应保留原响应，核对后再决定下一步，不自动重试交易。
