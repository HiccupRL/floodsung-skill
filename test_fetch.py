import requests
url = "https://theory.gmw.cn/node_31483.htm"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
try:
    r = requests.get(url, headers=headers, timeout=10)
    print("Status:", r.status_code)
    print("Content len:", len(r.text))
except Exception as e:
    print("Error:", e)
