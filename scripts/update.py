#!/usr/bin/env python3
"""Sabtyar daily official-link crawler. It never invents dates."""
from pathlib import Path
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen
from html.parser import HTMLParser
from datetime import datetime,timezone
import json,re

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/"data/registrations.json"; SOURCES=BASE/"data/sources.json"; REPORT=BASE/"data/bot-report.json"
UA="Mozilla/5.0 (compatible; SabtyarLinkBot/1.0; +https://sabtyar-ir.pages.dev/)"
KEYWORDS=("ثبت نام","ثبت‌نام","ثبتنام","استخدام","پذیرش","آزمون","تقاضا","درخواست","سامانه ثبت")
def norm(s):
    return re.sub(r"\s+"," ",(s or "").lower().replace("ي","ی").replace("ك","ک").replace("\u200c"," ")).strip()
class Parser(HTMLParser):
    def __init__(self,base): super().__init__(); self.base=base; self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            d=dict(attrs); u=d.get("href")
            if u:self.links.append((urljoin(self.base,u),""))
    def handle_data(self,data):
        if self.links and data.strip(): self.links[-1]=(self.links[-1][0],(self.links[-1][1]+" "+data.strip())[:240])
def fetch(u):
    req=Request(u,headers={"User-Agent":UA,"Accept":"text/html"})
    with urlopen(req,timeout=20) as r:
        return r.geturl(),r.read(700000).decode("utf-8","ignore")
def okdomain(u,d):
    h=(urlparse(u).hostname or "").lower().lstrip("www."); d=d.lower().lstrip("www.")
    return h==d or h.endswith("."+d)
def score(u,t,item):
    h=norm(u+" "+t); sc=sum(2 for k in KEYWORDS if k in h)
    for w in re.findall(r"[\w\u0600-\u06ff]{3,}",norm(item.get("title"))):
        if w in h: sc+=2
    if norm(item.get("category")) in h: sc+=1
    return sc
def main():
    data=json.loads(DATA.read_text(encoding="utf-8")); sources=json.loads(SOURCES.read_text(encoding="utf-8"))
    report={"checked_at":datetime.now(timezone.utc).isoformat(),"updated":[],"candidates":[],"errors":[]}
    for src in sources["sources"]:
        if not src.get("enabled"): continue
        domain=src["official_domain"]; found=[]
        for page in src.get("crawl_pages",[src["url"]]):
            try:
                final,body=fetch(page); p=Parser(final); p.feed(body)
                for u,t in p.links:
                    if okdomain(u,domain):
                        sc=score(u,t,{"title":"","category":src.get("category","")})
                        if sc>=3: found.append((sc,u,t))
            except Exception as e: report["errors"].append({"source":src["name"],"page":page,"error":str(e)})
        seen=set(); found=[x for x in sorted(found,reverse=True) if not (x[1] in seen or seen.add(x[1]))]
        for item in data["items"]:
            if norm(item.get("source"))!=norm(src["name"]) and norm(item.get("category"))!=norm(src.get("category")): continue
            ranked=sorted((score(u,t,item),u,t) for _,u,t in found)[::-1]
            if ranked and ranked[0][0]>=7 and ranked[0][1]!=item.get("url"):
                old=item.get("url"); item["url"]=ranked[0][1]; item["link_checked"]=datetime.now(timezone.utc).isoformat()
                report["updated"].append({"title":item["title"],"old":old,"new":item["url"]})
        report["candidates"] += [{"source":src["name"],"url":u,"text":t,"score":s} for s,u,t in found[:20]]
    data["updated"]=datetime.now(timezone.utc).isoformat()
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("updated:",len(report["updated"]),"candidates:",len(report["candidates"]),"errors:",len(report["errors"]))
if __name__=="__main__": main()
