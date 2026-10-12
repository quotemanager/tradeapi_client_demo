# 通达信客户端接口

默认地址 `http://127.0.0.1:18769`。除 `GET /health` 外，请求头包含 `Authorization: Bearer <本机token>`。POST 使用UTF-8 JSON对象和 `Content-Type: application/json`。

## 查询

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/health` | 服务存活 |
| GET | `/v1/status` | 登录状态，检查result.logged_in |
| GET | `/v1/queries/funds` | 资金 |
| GET | `/v1/queries/holdings` | 持仓 |
| GET | `/v1/queries/orders` | 当日委托 |
| GET | `/v1/queries/trades` | 当日成交 |
| GET | `/v1/queries/cancelable_orders` | 可撤单列表，仅查询 |
| GET | `/v1/queries/shareholders` | 股东代码，可含资金账号 |

查询结果位于 `result.records`，`count` 为记录数。检查外层与result中的ok；`truncated=true` 不能当作完整结果。金额、价格等通常为字符串，字段可能缺失或为空。

## 委托

`POST /v1/orders`，主动调用即发送一次真实委托，无需confirmed等参数。

```json
{
  "request_id": "order-example-000001",
  "account_variant": "normal",
  "side": "buy",
  "security_code": "600000",
  "price": "10.00",
  "quantity": 100
}
```

以上仅展示格式，不是建议下单。

| 字段 | 说明 |
| --- | --- |
| request_id | 必填，8至80位ASCII字母、数字、下划线或短横线；每笔新动作唯一，发送前保存 |
| account_variant | 必填，normal普通、margin两融，与当前账户一致 |
| side | 必填，buy买入、sell卖出、finance_buy融资买入 |
| security_code | 必填，六位字符串，保留前导零 |
| price | 必填，正数文本，最多六位小数，不传JSON浮点数 |
| quantity | 必填，正整数，单位股或份，满足证券规则 |

融资买入要求margin账户及相应权限。查询、委托不需要调用方传入券商密码或股东代码。

成功回执示例，虚构数据并省略其他字段：

```json
{
  "ok": true,
  "request_id": "order-example-000001",
  "automatic_retry": false,
  "result": {"accepted": true, "order_id": "0005", "message": null, "status": "accepted"}
}
```

这表示受理回执，不代表成交。`result.accepted=false` 表示明确失败，`null` 表示需核对；合同号保持字符串，不推测缺失值。

## 撤单

`POST /v1/cancellations`

```json
{"request_id":"cancel-example-000001","account_variant":"normal","order_id":"0005"}
```

仅撤当前账户可撤列表中唯一匹配的目标。合同号不唯一、缺少信息或已不可撤会拒绝发送；撤单时订单也可能已经成交。

## 动作结果与错误

`GET /v1/actions/<request_id>` 只读取保存的动作结果，不重复交易。同ID同参数可返回保存结果，改变参数会冲突。超时或未知结果不能更换ID自动重发；查不到记录也不能证明未申报。

错误通常为 `{"ok":false,"error":{"code":"错误代码","message":"错误说明"}}`。HTTP200也可能业务失败，必须解析JSON。完整运行包用户说明是对应版本的参数依据。
