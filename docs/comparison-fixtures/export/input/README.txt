本地供应商导出工具使用说明：vendor_export.py --format jsonl --out <文件>。本版本不支持 CSV。JSONL 导出保留所有 revision，业务过滤和去重由调用方决定。orders.json 是原始记录，可直接读取。所有金额为整数分。仅依赖 Python 标准库。
