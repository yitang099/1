#!/usr/bin/env python3
"""Dump all contentsList FAQ data + titles (no auth)"""
import requests, re, json, urllib3
urllib3.disable_warnings()
BASE = "https://us-campus.co.kr"
H = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
catalog = []

for mid in range(1380, 1430):
    r = requests.post(BASE + "/study/contentsList", data={"id": mid, "code": "FAQ"},
                      headers=H, verify=False, timeout=10)
    try:
        j = r.json()
        cl = j.get("contentsList", "")
        if not cl or len(cl) < 150:
            continue
        # extract section titles
        sections = re.findall(r"<strong>([^<]+)</strong>", cl)
        articles = re.findall(r"STUDY\.article\('(\d+)'\)", cl)
        titles = re.findall(r"<a href=\"javascript:STUDY\.article\('(\d+)'\);\">([^<]*)</a>", cl)
        if articles or sections:
            entry = {"menu_id": mid, "sections": sections, "article_count": len(articles),
                     "articles": articles, "titles": titles, "html_len": len(cl)}
            catalog.append(entry)
            print(f"menu={mid} sections={len(sections)} articles={len(articles)}", flush=True)
    except:
        pass

with open("/workspace/us-campus-recon/deep21_course_catalog.json", "w") as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)
print(f"SAVED {len(catalog)} menus, total articles={sum(x['article_count'] for x in catalog)}", flush=True)
