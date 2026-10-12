# C++ 示例

Windows、Visual Studio C++构建工具、CMake 3.20或以上，C++17。默认WinHTTP调用，也可动态加载运行包DLL。

在仓库根目录构建。首次配置需要下载固定版本nlohmann/json，CMake检查下载SHA256：

```powershell
cmake -S examples/cpp -B build/cpp -A x64
cmake --build build/cpp --config Release
```

设置 [连接环境变量](../../docs/quick-start.md) 后执行：

```powershell
.\build\cpp\Release\tradeapi_client_demo.exe tdx query funds
.\build\cpp\Release\tradeapi_client_demo.exe ths query holdings
.\build\cpp\Release\tradeapi_client_demo.exe tdx order config/tdx-buy.local.json
# 显式发送一次真实委托：
.\build\cpp\Release\tradeapi_client_demo.exe tdx order config/tdx-buy.local.json --execute
```

买卖、融资买入、同花顺预览及撤单命令同 [首页](../../README.md)。在末尾添加 `--dll` 改为DLL方式，需设置对应产品HOME；不会另外发HTTP请求。64位程序加载x64 DLL，32位加载x86 DLL；不要把客户端位数当成调用程序位数。

DLL使用cdecl/UTF-8，输出不足只读取同线程缓存，见 [SDK与DLL](../../docs/sdk-dll.md)。WinHTTP不使用代理或跟随重定向，响应上限16MiB，不自动重发交易。
