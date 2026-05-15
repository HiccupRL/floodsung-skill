import sys, traceback, yaml
sys.path.insert(0, '.')
from scripts.scraper import Client, scrape_mia

try:
    cfg = yaml.safe_load(open('config/sources.yaml', encoding='utf-8'))
    src = [s for s in cfg['sources'] if s['id'] == 'cpc_people_maozedong'][0]
    c = Client('chinese-thought-corpus-skill/0.1', 0.8, 30, False)
    print('Starting scrape_mia', flush=True)
    out = scrape_mia(c, src, 2)
    print('Items:', len(out), flush=True)
except Exception as e:
    with open('error.log', 'w') as f:
        traceback.print_exc(file=f)
