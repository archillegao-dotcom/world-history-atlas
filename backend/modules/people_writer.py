"""模块「文学家」：作家、诗人、小说家、剧作家等（Wikidata P106）。"""
from ._people_base import PeopleModule

MODULE = PeopleModule("people_writer", "文学家", "people_writer.json.gz", keywords=("作家", "诗人", "詩人", "小说", "小說", "剧作", "劇作", "散文", "词人", "詞人", "writer", "poet", "novelist", "playwright", "dramatist", "author", "essayist", "literary"),
                      order=20)
