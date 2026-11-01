"""模块「哲学家」（Wikidata P106 = Q4964182 哲学家）。"""
from ._people_base import PeopleModule

MODULE = PeopleModule("people_philosopher", "哲学家", "people_philosopher.json.gz", keywords=("哲学", "哲學", "思想家", "philosopher", "thinker"),
                      order=30)
