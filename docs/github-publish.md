# GitHub 发布准备

推荐仓库名：`tradeapi-client-demo`，选择公开仓库。

推荐简介：

> A股程序化交易接口多语言示例，提供通达信与同花顺客户端接口的Python、C++、C#、Java、Node.js、Go调用版本，覆盖查询、买卖、融资买入和撤单，支持HTTP、Python SDK和DLL接入。运行包获取与咨询：Telegram @tradeapi8。

可选Topics：`tradeapi`、`tdx`、`tonghuashun`、`quant-trading`、`python`、`cpp`、`csharp`、`java`、`nodejs`、`golang`、`trading-api`。

## 上传前检查

本地Git仓库已初始化为main，但没有创建远端或推送。先检查README、联系方式和许可，再执行：

```powershell
python tools/check_public_files.py
git status --short
git add .
git diff --cached --stat
python tools/check_public_files.py
```

确认没有运行包、账户信息或本地文件后，再自行提交和关联自己的仓库：

```powershell
git commit -m "Add TDX and THS multilingual client examples"
git remote add origin https://github.com/YOUR_NAME/tradeapi-client-demo.git
git push -u origin main
```

不要使用 `git add -f` 添加被忽略的文件。构建目录中的可执行文件、SDK工具及mock DLL不上传；运行包和官方客户端须单独获取。

GitHub Actions只做编译和模拟服务器测试，不使用真实账户或token，不会交易。发布后查看Actions是否成功，不要把CI通过理解为券商兼容性或成交验证。
