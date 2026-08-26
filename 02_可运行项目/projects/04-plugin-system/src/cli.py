"""历史 CLI 兼容入口（版本 0.3.0）。

完成可编辑安装后，新代码应使用 ``course-safe-plugins``；保留本文件是为了
让早期章节中的 ``python src/cli.py`` 仍调用同一实现。
"""

from safe_plugin_system.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
