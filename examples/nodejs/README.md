# Node.js 示例

Node.js 18或以上，无需npm依赖；使用标准库http，不读取代理配置，不跟随重定向，不自动重试。

在仓库根目录设置 [连接环境变量](../../docs/quick-start.md)：

```powershell
node examples/nodejs/demo.js tdx status
node examples/nodejs/demo.js tdx query funds
node examples/nodejs/demo.js ths query holdings
node examples/nodejs/demo.js tdx order config/tdx-buy.local.json
# 上一行仅打印参数，下面才发送一次真实委托：
node examples/nodejs/demo.js tdx order config/tdx-buy.local.json --execute
node examples/nodejs/demo.js ths preview-cancel config/ths-cancel.local.json
node examples/nodejs/demo.js ths submit-cancel YOUR_READY_PREVIEW_ID --execute
```

所有查询和交易命令与 [首页](../../README.md) 相同，两融融资买入使用对应JSON模板。可以从demo.js导出的call函数复用HTTP部分。

JSON响应原样展示，HTTP200和退出码0不表示券商受理；结果未知时不重复提交。
