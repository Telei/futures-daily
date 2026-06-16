"""交易所元数据。"""

# 交易所代码 -> 中文名称
EXCHANGES: dict[str, str] = {
    "SHFE": "上海期货交易所",
    "DCE": "大连商品交易所",
    "CZCE": "郑州商品交易所",
    "CFFEX": "中国金融期货交易所",
    "INE": "上海国际能源交易中心",
    "GFEX": "广州期货交易所",
}


def exchange_name(code: str) -> str:
    return EXCHANGES.get(code.upper(), code)
