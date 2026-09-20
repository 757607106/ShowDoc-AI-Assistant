# 文件命名速查

工程代码统一使用英文命名，中文只用于用户界面文本、业务分类和文档正文。

```text
Python 模块       snake_case.py
Python 包         lowercase 或 snake_case
类                PascalCase
函数 / 变量       snake_case
常量              UPPER_SNAKE_CASE
测试              test_<module>.py
Markdown          kebab-case.md
CSS / JS          lowercase-kebab-case 或现有短文件名
```

命名应体现职责，而不是实现细节。例如使用 `web_discovery.py` 表示网页发现能力，使用 `web_adapters.py` 表示站点适配器集合；不要使用 `new.py`、`utils2.py`、`临时测试.py` 等无法表达边界的名称。
