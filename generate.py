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
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Referer": BASE_URL  # Важно для обхода защиты картинок
}

all_poses = []
seen_titles = set()

print("Начинаем парсинг...")
for cat_name, cat_url in CATEGORIES.items():
    print(f"Смотрим категорию: {cat_name}")
    try:
        r = requests.get(cat_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Ищем ВСЕ ссылки, ведущие на позы
        links = soup.find_all("a", href=lambda h: h and "/pozy/" in h)
        
        for link in links:
            title = link.get_text(strip=True)
            if not title or len(title) < 3 or title in seen_titles:
                continue
            
            seen_titles.add(title)
            
            # Ищем картинку: внутри ссылки, или в её родительском блоке
            img_tag = link.find("img") or link.parent.find("img")
            
            # Если не нашли, ищем на 2 уровня выше
            if not img_tag:
                container = link.find_parent(['article', 'div'])
                if container:
                    img_tag = container.find("img")
            
            base64_img = ""
            if img_tag:
                # Пытаемся достать ссылку из разных атрибутов (lazy load)
                img_src = (img_tag.get("src") or 
                           img_tag.get("data-src") or 
                           img_tag.get("data-lazy-src") or 
                           img_tag.get("srcset"))
                
                if img_src:
                    # Если это srcset, берем первую ссылку
                    if "," in img_src: img_src = img_src.split(",")[0].split(" ")[0]
                    
                    img_url = urljoin(BASE_URL, img_src)
                    try:
                        img_data = requests.get(img_url, headers=HEADERS, timeout=10).content
                        # Проверяем, что это реально картинка, а не заглушка
                        if len(img_data) > 1000:  
                            b64 = base64.b64encode(img_data).decode('utf-8')
                            base64_img = f"data:image/jpeg;base64,{b64}"
                    except Exception as e:
                        print(f"  Ошибка загрузки картинки: {img_url}")

            # Описание (если есть)
            desc_tag = link.parent.find("p") if link.parent else None
            desc = desc_tag.get_text(strip=True) if desc_tag else "Описание отсутствует. Нажмите кнопку еще раз, чтобы увидеть другую позу."

            all_poses.append({
                "category": cat_name,
                "title": title,
                "description": desc,
                "image": base64_img
            })
            print(f"  + {title} (картинка: {'ЕСТЬ' if base64_img else 'НЕТ'})")
            
        time.sleep(1)
    except Exception as e:
        print(f"  Критическая ошибка в {cat_name}: {e}")

print(f"\nВсего собрано поз: {len(all_poses)}")

# Генерация HTML
html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Random Sex Position Picker</title>
    <style>
        body {{ background-color: #1a1a1a; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; padding: 20px; margin: 0; }}
        .controls {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; justify-content: center; }}
        select {{ padding: 10px; font-size: 16px; background: #333; color: white; border: none; border-radius: 5px; }}
        button {{ background-color: #e50914; color: white; border: none; padding: 12px 24px; font-size: 18px; font-weight: bold; border-radius: 5px; cursor: pointer; }}
        .card {{ background: #2a2a2a; border-radius: 10px; padding: 20px; max-width: 600px; width: 100%; text-align: center; display: none; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
        .card img {{ max-width: 100%; max-height: 500px; border-radius: 8px; margin-bottom: 15px; object-fit: cover; }}
        h2 {{ color: #e50914; margin-top: 0; }}
        .placeholder {{ width: 100%; height: 200px; background: #333; display: flex; align-items: center; justify-content: center; border-radius: 8px; margin-bottom: 15px; color: #777; font-size: 14px; }}
    </style>
</head>
<body>
    <h1>🎲 Случайная поза</h1>
    <div class="controls">
        <select id="categorySelect"><option value="all">Все категории</option></select>
        <button id="randomBtn">Показать позу</button>
    </div>
    <div id="poseCard" class="card">
        <div id="imageContainer"></div>
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
                
                let imgContainer = document.getElementById("imageContainer");
                if (pose.image) {{
                    imgContainer.innerHTML = `<img src="${{pose.image}}" alt="Поза">`;
                }} else {{
                    imgContainer.innerHTML = `<div class="placeholder">Картинка не найдена (сайт заблокировал загрузку)</div>`;
                }}
            }});
        }});
    </script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Готово! index.html сгенерирован.")
