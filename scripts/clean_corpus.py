import json
import re
from pathlib import Path

def clean_text(text):
    # Remove markdown images: ![alt](url)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Remove markdown links: [text](url) -> text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Remove Gushiwen UI noise
    text = re.sub(r'古文岛\s*推荐\s*诗文\s*名句\s*古籍\s*作者\s*字词', '', text)
    text = re.sub(r'APP\s*登录', '', text)
    text = re.sub(r'东北一枝花.*?朗诵：琼花\)', '', text, flags=re.DOTALL)
    text = re.sub(r'播放列表.*?单曲播放', '', text, flags=re.DOTALL)
    text = re.sub(r'您的浏览器不支持.*?元素。', '', text)
    text = re.sub(r'初始的播放列表项', '', text)
    text = re.sub(r'© \d{4} 古诗文网.*', '', text)
    text = re.sub(r'© \d{4} 古文岛.*', '', text)
    text = re.sub(r'完善\s*写景\s*抒情.*', '', text)
    text = re.sub(r'上一章.*?下一章', '', text, flags=re.DOTALL)
    text = re.sub(r'目录', '', text)
    
    # Remove GMW/CPC UI noise
    text = re.sub(r'您当前的位置：.*?\n', '', text)
    text = re.sub(r'中国共产党新闻.*?>>.*?\n', '', text)
    text = re.sub(r'上一页.*?\n', '', text)
    text = re.sub(r'下一页.*?\n', '', text)
    text = re.sub(r'毛泽东文集.*?条.*?\n', '', text)
    text = re.sub(r'毛泽东选集.*?\n', '', text)
    text = re.sub(r'第一卷.*?第八卷', '', text, flags=re.DOTALL)
    text = re.sub(r'选集文集.*?>>.*?\n', '', text)
    
    # Remove extra blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def main():
    corpus_file = Path('data/corpus/all.json')
    if not corpus_file.exists():
        print("all.json not found")
        return

    with open(corpus_file, 'r', encoding='utf-8') as f:
        items = json.load(f)

    valid_items = []
    for item in items:
        title = item.get('title', '')
        
        # Filter out navigation/list pages
        if '全部导航' in title or '首页' in title or title == '导航' or title.startswith('毛泽东文集') or '选集文集' in title or '列表' in title or '毛泽东选集' in title or '毛泽东集' in title:
            print(f"Skipping fake/nav article: {title}")
            continue
            
        cleaned = clean_text(item['text'])
        
        # If the text is too short after cleaning, it's probably an index or noise
        if len(cleaned) < 100:
            print(f"Skipping too short after clean: {title}")
            continue
            
        item['text'] = cleaned
        valid_items.append(item)

    print(f"\nFiltered out {len(items) - len(valid_items)} items. Remaining: {len(valid_items)}\n")

    # Save back all.json
    with open(corpus_file, 'w', encoding='utf-8') as f:
        json.dump(valid_items, f, ensure_ascii=False, indent=2)

    # Re-dump specific collections
    by = {}
    for it in valid_items:
        by.setdefault(it["collection"], []).append(it)
        
    for name, recs in by.items():
        with open(f'data/corpus/{name}.json', 'w', encoding='utf-8') as f:
            json.dump(recs, f, ensure_ascii=False, indent=2)
            
        lines = [f"# {name}\n", f"Total: {len(recs)}\n"]
        for r in recs:
            lines += ["\n---\n", f"## {r['title']}\n", f"- author: {r['author']}",
                      f"- group: {r['group']}", f"- source: {r['source_url']}",
                      f"- license: {r['license_note']}", f"- risk: {r['risk_note']}\n", r["text"], ""]
        with open(f'data/corpus/{name}.md', 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
            
if __name__ == '__main__':
    main()
