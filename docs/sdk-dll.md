# Python SDK 与 DLL

两套运行包均提供SDK和DLL，它们调用本机API，与HTTP方式共享当前账户和权限。不会代替用户登录，也不是脱离客户端的券商直连接口。本示例仓库不包含二进制库和SDK内部实现。

## Python SDK

设置 `TRADEAPI_TDX_HOME` 或 `TRADEAPI_THS_HOME` 为包含 `start-api.bat` 的完整运行包目录，然后调用：

```powershell
$env:TRADEAPI_TDX_HOME = 'D:\TradeApiTDX'
$env:TRADEAPI_THS_HOME = 'D:\TradeApiTHS'
python examples/python/sdk_demo.py tdx query funds
python examples/python/sdk_demo.py ths query funds
```

示例通过运行包 `sdk/python` 导入 `tradeapi_tdx.Client` 或 `tradeapi_ths.Client`，使用公开 `Client.from_directory` 和 `call` 方法，命令与HTTP示例相同。也可在自己程序中使用这些公开便捷方法：

| 通达信 | 同花顺 |
| --- | --- |
| status、query | status、query |
| send_order、cancel_order | preview_order、preview_cancel |
| action_status | poll_preview、submit_order、submit_cancel、action_status |

同花顺委托须预览就绪后提交，不是调用send_order直接传股票参数。SDK错误响应应保留，不自动轮询、提交或重试。

## DLL

需要对应产品URL、TOKEN、HOME三个环境变量。选择 `build/x86/tradeapi_tdx.dll` 或 `build/x64/tradeapi_tdx.dll`；同花顺为对应的tradeapi_ths.dll。按**调用进程位数**选择，不按客户端位数选择。

示例入口：

```powershell
python examples/python/dll_demo.py tdx query funds
python examples/python/dll_demo.py ths query funds
# C++ / C# 编译后，在其命令末尾添加 --dll；各语言README有构建方法。
```

这些示例使用相同的公开C ABI：

```c
int TradeApi_Initialize(const char* base_url, const char* token);
int TradeApi_Call(const char* method, const char* path, const char* json,
                  char* output, uint32_t capacity, uint32_t* required);
int TradeApi_GetLastResponse(char* output, uint32_t capacity, uint32_t* required);
uint32_t TradeApi_GetLastHttpStatus(void);
```

调用约定cdecl，字符串UTF-8，输出缓冲区由调用方提供，required包含末尾NUL。具体头文件以运行包 `sdk/tradeapi_tdx.h` 或 `sdk/tradeapi_ths.h` 为准。

先分配64KiB，返回3时按required扩容，**在同一线程调用GetLastResponse读取缓存**，不得再次调用原委托或撤单函数。缓存复制成功不等于原HTTP成功，还要检查GetLastHttpStatus及JSON。

| DLL返回码 | 调用方处理 |
| ---: | --- |
| 0 | 收到HTTP200，继续检查业务JSON |
| 1 | 参数无效 |
| 2 | 传输或响应失败，交易结果可能未知，不自动重发 |
| 3 | 缓冲区不足，只取同线程缓存 |
| 4 | 非HTTP200，保留错误JSON |

DLL模式同样支持本仓库的查询、预览、提交、撤单和结果命令；真实提交仍需显式选择 `--execute`。DLL和API都需要完整运行包，不要只复制一个DLL给用户。
