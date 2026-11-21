"""从当前 skill 的源码启动 stdio 服务，保留调用者的工作目录。"""

import sys
from pathlib import Path

if __name__ == "__main__":
    source = Path(__file__).resolve().parent / "src"
    if not (source / "rigol_dho900_mcp" / "server.py").is_file():
        sys.exit(f"随包服务不完整，请重新复制整个 skill 目录：{source}")
    sys.path.insert(0, str(source))
    from rigol_dho900_mcp.server import main

    main()
