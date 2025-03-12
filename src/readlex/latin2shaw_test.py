from readlex import latin2shaw


def test_latin2shaw():
    text_latin = """
ANDROCLES AND THE LION

PROLOGUE

Overture: forest sounds, roaring of lions, Christian hymn faintly.
    """
    text_shaw = """
·𐑨𐑯𐑛𐑮𐑩𐑒𐑤𐑰𐑟 𐑯 𐑞 𐑤𐑲𐑩𐑯

𐑐𐑮𐑴𐑤𐑪𐑜

𐑴𐑝𐑼𐑗𐑫𐑼: 𐑓𐑪𐑮𐑦𐑕𐑑 𐑕𐑬𐑯𐑛𐑟, 𐑮𐑹𐑦𐑙 𐑝 𐑤𐑲𐑩𐑯𐑟, 𐑒𐑮𐑦𐑕𐑗𐑩𐑯 𐑣𐑦𐑥 𐑓𐑱𐑯𐑑𐑤𐑦.
    \n"""  # TODO: the trailing newline here seems to be added by latin2shaw, not sure if that's a bug?

    assert latin2shaw(text_latin) == text_shaw
