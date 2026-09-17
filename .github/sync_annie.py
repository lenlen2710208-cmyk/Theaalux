import asyncio, json, pathlib, re
from datetime import datetime, timezone
from playwright.async_api import async_playwright

OUT=pathlib.Path('data'); OUT.mkdir(exist_ok=True)
PAGES=['https://annie-nikki.homes/items','https://annie-nikki.homes/stages?type=arena']

async def main():
    candidates=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        page=await browser.new_page()
        async def on_response(resp):
            u=resp.url
            if resp.request.resource_type not in {'fetch','xhr'} and not re.search(r'json|api|data',u,re.I): return
            try:
                ct=resp.headers.get('content-type','')
                if 'json' not in ct.lower() and not u.endswith('.json'): return
                text=await resp.text()
                if len(text)<1000: return
                data=json.loads(text)
                arr=data if isinstance(data,list) else data.get('items') if isinstance(data,dict) else None
                if isinstance(arr,list) and len(arr)>=100:
                    candidates.append((len(arr),u,data))
            except Exception:
                pass
        page.on('response', on_response)
        for url in PAGES:
            try:
                await page.goto(url,wait_until='networkidle',timeout=90000)
                await page.wait_for_timeout(5000)
            except Exception as e:
                print('page error',url,e)
        await browser.close()
    candidates.sort(key=lambda x:x[0],reverse=True)
    if not candidates:
        raise SystemExit('No public JSON dataset was discovered; leaving existing data untouched.')
    n,url,data=candidates[0]
    arr=data if isinstance(data,list) else data.get('items')
    # Only accept a large item-like collection. This prevents accidentally saving a stage list as the item DB.
    itemish=sum(1 for x in arr[:200] if isinstance(x,(list,dict)))
    if n<1000 or itemish<100:
        raise SystemExit(f'Discovered JSON was not large enough for the item database: {n}')
    pathlib.Path('data/vn-items.json').write_text(json.dumps(arr,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    meta={'source_url':url,'count':n,'synced_at':datetime.now(timezone.utc).isoformat(),'note':'Discovered from public network requests made by Annie Nikki Homes. Verify that this dataset represents the VNG Vietnam server before treating it as authoritative.'}
    pathlib.Path('data/source-meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(meta,ensure_ascii=False))

asyncio.run(main())
