# Python 示例

Python 3.10或以上；HTTP示例只使用标准库，无需pip安装。本例不需要32位Python；DLL模式选择与当前Python进程位数一致的库。

在仓库根目录设置 [连接环境变量](../../docs/quick-start.md)，然后执行：

```powershell
python examples/python/demo.py tdx status
python examples/python/demo.py tdx query funds
python examples/python/demo.py ths query holdings
python examples/python/demo.py ths preview-order config/ths-buy.local.json
python examples/python/demo.py ths poll-order YOUR_PREVIEW_ID
# ready=true且已核对参数后，显式发送一次真实委托：
python examples/python/demo.py ths submit-order YOUR_PREVIEW_ID --execute
```

`client.py` 是本仓库公开的HTTP调用封装，可在自己的程序中复用：

```python
import os
import sys
sys.path.insert(0, "examples/python")
from client import call
status, response = call("http://127.0.0.1:18769", os.environ["TRADEAPI_TDX_TOKEN"],
                        "GET", "/v1/queries/funds")
print(status, response)
```

`sdk_demo.py` 加载外部运行包的公开Python SDK；`dll_demo.py` 加载运行包DLL，查询和交易命令相同，见 [SDK与DLL](../../docs/sdk-dll.md)。SDK模式由HOME读取运行包连接配置；HTTP模式由URL和TOKEN环境变量读取。

完整买卖、融资买入、撤单示例见 [首页](../../README.md)。示例不重试、不自动提交预览；HTTP成功仍须检查业务状态。
