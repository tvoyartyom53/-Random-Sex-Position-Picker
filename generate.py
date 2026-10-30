import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import base64
import json
import time

CATEGORIES = {
    "Вагинальный секс": "https://medow.club/pozy/vid-seksa/vaginalnyj-seks",
    "Анальный секс": "https://medow.club/pozy/vid-seksa/analnyj-seks",
    "Оральный секс": "https://medow.club/pozy/vid-seksa/oralnyj-seks",
    "Поза 69": "https://medow.club/pozy/vid-seksa/poza-69",
    "Минет": "https://medow.club/pozy/vid-seksa/minet",
    "Кунилингус": "https://medow.club/pozy/vid-seksa/kunilingus",
}

BASE_URL = "https://medow.club"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

all_poses = []
seen_titles = set()

print("Начинаем парсинг...")
for cat_name, cat_url in CATEGORIES.items():
    try:
        r = requests.get(cat_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Ищем все ссылки на позы
        links = soup.find_all("a", href=lambda h: h and "/pozy/" in h)
        
        for link in links:
            title = link.get_text(strip=True)
            if not title or len(title) < 3 or title in seen_titles:
                continue
            
            seen_titles.add(title)
            
            # Ищем картинку рядом со ссылкой
            img_tag = link.find("img") or link.parent.find("img")
            base64_img = ""
            
            if img_tag:
                img_src = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-lazy-src")
                if img_src:
                    img_url = urljoin(BASE_URL, img_src)
                    try:
                        img_data = requests.get(img_url, headers=HEADERS, timeout=10).content
                        b64 = base64.b64encode(img_data).decode('utf-8')
                        base64_img = f"data:image/jpeg;base64,{b64}"
                    except: pass

            all_poses.append({
                "category": cat_name,
                "title": title,
                "description": "Нажмите кнопку еще раз, чтобы увидеть другую позу.",
                "image": base64_img
            })
            print(f"Скачано: {title}")
    except Exception as e:
        print(f"Ошибка в {cat_name}: {e}")

# Генерация HTML
html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Random Sex Position Picker</title>
    <style>
        body {{ background-color: #1a1a1a; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; padding: 20px; }}
        .controls {{ display: flex; gap: 10px; margin-bottom: 20px; }}
        select {{ padding: 10px; font-size: 16px; background: #333; color: white; border: none; border-radius: 5px; }}
        button {{ background-color: #e50914; color: white; border: none; padding: 12px 24px; font-size: 18px; font-weight: bold; border-radius: 5px; cursor: pointer; }}
        .card {{ background: #2a2a2a; border-radius: 10px; padding: 20px; max-width: 600px; width: 100%; text-align: center; display: none; }}
        .card img {{ max-width: 100%; max-height: 500px; border-radius: 8px; margin-bottom: 15px; }}
        h2 {{ color: #e50914; }}
    </style>
</head>
<body>
    <h1>🎲 Случайная поза</h1>
    <div class="controls">
        <select id="categorySelect"><option value="all">Все категории</option></select>
        <button id="randomBtn">Показать позу</button>
    </div>
    <div id="poseCard" class="card">
        <img id="poseImage" src="" style="display:none;">
        <h2 id="poseTitle"></h2>
        <p id="poseDesc"></p>
    </div>
    <script>
        const posesData = {json.dumps(all_poses, ensure_ascii=False)};
        document.addEventListener("DOMContentLoaded", () => {{
            const catSelect = document.getElementById("categorySelect");
            const btn = document.getElementById("randomBtn");
            const card = document.getElementById("poseCard");
            
            const categories = [...new Set(posesData.map(p => p.category))];
            categories.forEach(c => {{
                let opt = document.createElement("option");
                opt.value = c; opt.textContent = c; catSelect.appendChild(opt);
            }});

            btn.addEventListener("click", () => {{
                let filtered = catSelect.value === "all" ? posesData : posesData.filter(p => p.category === catSelect.value);
                if (filtered.length === 0) return;
                
                let pose = filtered[Math.floor(Math.random() * filtered.length)];
                card.style.display = "block";
                document.getElementById("poseTitle").textContent = pose.title;
                document.getElementById("poseDesc").textContent = pose.description;
                
                let img = document.getElementById("poseImage");
                if (pose.image) {{ img.src = pose.image; img.style.display = "block"; }}
                else {{ img.style.display = "none"; }}
            }});
        }});
    </script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Готово!")
