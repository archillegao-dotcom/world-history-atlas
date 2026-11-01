"""模块「政治家」：政治家、君主、国家元首、政府首脑（Wikidata P106）。"""
from ._people_base import PeopleModule

MODULE = PeopleModule("people_politician", "政治家", "people_politician.json.gz", keywords=("政治", "国王", "國王", "皇帝", "君主", "总统", "總統", "首相", "总理", "總理", "女王", "王后", "苏丹", "蘇丹", "沙皇", "法老", "politician", "statesman", "king", "queen", "emperor", "empress", "president", "prime minister", "monarch", "ruler", "sultan", "tsar", "pharaoh", "chancellor", "governor"),
                      order=40)
