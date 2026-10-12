# 模拟测试

测试启动临时本机HTTP服务器，用虚构令牌和响应验证示例，不连接券商、官方客户端或已经运行的交易API。

```powershell
python -m unittest discover -s tests -v
```

Python必须可用；若PATH中有Node则同时验证Node。已构建的C++、C#、Java、Go示例也会被自动纳入测试。可用DEMO_NODE、DEMO_DOTNET、DEMO_JAVA显式选择解释器。

覆盖查询映射、只读默认值、委托与撤单dry-run、一次mock提交、同花顺预览/查询/提交、融资参数、前导零、HTTP错误不重发、重定向不跟随、文档本地链接。

可选mock DLL测试：构建C++时增加 `-DDEMO_BUILD_TEST_FIXTURES=ON`。这份DLL只返回虚构JSON，无网络与客户端调用，测试Python/C++/C#在缓冲区不足时只复制缓存、保持原HTTP错误、不再次申报。Python SDK示例另用临时模拟SDK验证，不包含商业SDK源码。

`DEMO_REQUIRED_RUNNERS=python,nodejs,cpp,csharp,java,go` 可要求六种语言均被测试，缺少任一种就失败。GitHub Actions构建各语言后使用此要求，不需要任何真实token或账户资料。

模拟测试不验证券商交易权限、实际成交或不同版本客户端兼容性。首次真实验证先查状态和资金；交易参数由使用者自行核对。
