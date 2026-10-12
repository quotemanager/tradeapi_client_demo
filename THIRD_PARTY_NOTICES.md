# 第三方依赖

本仓库自行编写的是调用示例，不包含官方客户端、商业运行包或受保护组件。

| 依赖 | 用途 | 上游与许可 |
| --- | --- | --- |
| nlohmann/json 3.12.0 | C++ JSON解析，CMake按固定SHA256下载 | [官方项目](https://github.com/nlohmann/json)、MIT；[对应发布](https://github.com/nlohmann/json/releases/tag/v3.12.0) |
| Gson 2.13.2 | Java JSON解析，Maven下载 | [官方项目](https://github.com/google/gson)、Apache 2.0 |

Python、Node.js和Go示例使用各自标准库；C#使用.NET库；C++ HTTP模式使用Windows WinHTTP。自行分发构建产物时，应保留所包含第三方组件的许可证。使用通达信或同花顺客户端须遵守其自身的使用约定，示例许可不替代这些约定。
