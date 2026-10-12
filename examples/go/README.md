# Go 示例

Go 1.22或以上，标准库HTTP，不需要第三方依赖。

在仓库根目录设置 [连接环境变量](../../docs/quick-start.md)，运行：

```powershell
go run ./examples/go/main.go tdx status
go run ./examples/go/main.go tdx query funds
go run ./examples/go/main.go ths query holdings
go run ./examples/go/main.go ths preview-order config/ths-buy.local.json
# ready=true并已核对后，显式发送一次真实委托：
go run ./examples/go/main.go ths submit-order YOUR_READY_PREVIEW_ID --execute
```

构建Windows可执行文件：

```powershell
go build -o build/go/tradeapi-client-demo.exe ./examples/go/main.go
.\build\go\tradeapi-client-demo.exe tdx query funds
```

其他命令同 [首页](../../README.md)。参数文件价格保持字符串，数量为整数；响应通过RawMessage保留数值原始表示，避免为展示而改变数值精度。

不读代理、不跟随重定向、不复用连接或自动重试。HTTP成功不代表券商受理；提交未知时先核对官方客户端。
