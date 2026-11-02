import urllib.request,urllib.parse,json,sys
def qids(titles, lang="en"):
    out={}
    for i in range(0,len(titles),40):
        u=f"https://{lang}.wikipedia.org/w/api.php?"+urllib.parse.urlencode({"action":"query","titles":"|".join(titles[i:i+40]),"prop":"pageprops","ppprop":"wikibase_item","redirects":1,"format":"json"})
        d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"wha-audit/0.1"})))
        red={}
        for r in d['query'].get('normalized',[])+d['query'].get('redirects',[]): red[r['to']]=red.get(r['from'],r['from'])
        for p in d['query']['pages'].values():
            out[red.get(p['title'],p['title'])]=(p['title'],p.get('pageprops',{}).get('wikibase_item'))
    return out
if __name__=="__main__":
    t=[x for x in sys.argv[1:]]
    o=qids(t)
    for x in t: print(x,'->',o.get(x))
