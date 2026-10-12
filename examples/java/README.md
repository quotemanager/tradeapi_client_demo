# Java 示例

JDK 17或以上、Maven 3.8或以上。使用本机HTTP，Gson负责JSON读写。

在仓库根目录构建：

```powershell
mvn -f examples/java/pom.xml package
```

设置 [连接环境变量](../../docs/quick-start.md)，执行：

```powershell
java -jar examples/java/target/tradeapi-client-demo-1.0.0.jar tdx query funds
java -jar examples/java/target/tradeapi-client-demo-1.0.0.jar ths query holdings
java -jar examples/java/target/tradeapi-client-demo-1.0.0.jar tdx order config/tdx-buy.local.json
# 显式发送一次真实委托：
java -jar examples/java/target/tradeapi-client-demo-1.0.0.jar tdx order config/tdx-buy.local.json --execute
```

其他查询、融资买入、同花顺预览、提交及撤单命令同 [首页](../../README.md)。配置路径相对仓库根目录，不要在target目录中执行。

不读取代理、不跟随重定向、不自动重发交易；HTTP和原始业务响应都会打印，退出码0不代表券商已经受理。
