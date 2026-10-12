# C# 示例

.NET 8 SDK。默认HttpClient调用，Windows上可添加 `--dll` 调用运行包中的cdecl DLL。

在仓库根目录设置 [连接环境变量](../../docs/quick-start.md)，直接运行：

```powershell
dotnet run --project examples/csharp -- tdx status
dotnet run --project examples/csharp -- tdx query funds
dotnet run --project examples/csharp -- ths query holdings
dotnet run --project examples/csharp -- ths preview-order config/ths-buy.local.json
# 预览就绪并已核对后，显式发送一次真实委托：
dotnet run --project examples/csharp -- ths submit-order YOUR_READY_PREVIEW_ID --execute
```

生成可复用的构建输出：

```powershell
dotnet build examples/csharp -c Release -o build/csharp
dotnet build/csharp/TradeApiClientDemo.dll tdx query funds
```

其他命令同 [首页](../../README.md)，融资买入使用对应模板。DLL模式例如 `... tdx query funds --dll`，需对应产品HOME、URL和TOKEN；按当前C#进程位数加载DLL。源码 `DllConsumer` 演示动态加载、UTF-8参数和缓冲区缓存复制，不需要将商业DLL放入此仓库。

HTTP200及退出码0不代表受理或成交；全部业务JSON保留，不自动重发交易。
