import random
import sys
from io import BytesIO
from urllib.parse import urljoin

import tkinter as tk
from tkinter import messagebox, ttk  # ttk для выпадающего списка

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Установите зависимости: pip install requests beautifulsoup4 Pillow")

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ---------- НАСТРОЙКИ КАТЕГОРИЙ ----------
# Ключ - то, что видит пользователь, значение - URL для парсинга
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

# ---------- ПАРСЕР ----------
def fetch_poses(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Ошибка сети: {e}")

    soup = BeautifulSoup(r.text, "html.parser")
    poses, seen = [], set()

    candidates = soup.select("article, .post, .entry, .position, .item, .card")
    if not candidates:
        candidates = soup.find_all("a", href=lambda h: h and "/pozy/" in h)

    for block in candidates:
        link_tag = block if block.name == "a" else block.find("a", href=True)
        if not link_tag: continue

        href = link_tag.get("href", "")
        if "/pozy/" not in href: continue

        title = link_tag.get_text(strip=True)
        if not title or len(title) < 3 or title in seen: continue
        seen.add(title)

        desc_tag = block.find("p") if block.name != "a" else None
        desc = desc_tag.get_text(strip=True) if desc_tag else ""

        img_tag = block.find("img") if block.name != "a" else None
        img_url = None
        if img_tag:
            src = (img_tag.get("src") or img_tag.get("data-src") or 
                   img_tag.get("data-lazy-src") or img_tag.get("data-original"))
            if src:
                img_url = urljoin(BASE_URL, src)

        poses.append({
            "title": title,
            "description": desc,
            "image_url": img_url,
            "page_url": urljoin(BASE_URL, href),
        })

    if not poses:
        raise RuntimeError("Не удалось найти позы. Возможно, сайт требует JS-рендеринг.")
    return poses

# ---------- GUI ----------
class PoseApp:
    def __init__(self, root):
        self.root = root
        self.poses = []
        self.image_cache = {}
        self._photo_ref = None
        self.current_category_url = CATEGORIES["Вагинальный секс"]

        root.title("Случайная поза")
        root.geometry("580x820")  # Чуть выше, чтобы влез комбобокс
        root.minsize(400, 500)
        root.configure(bg="#1a1a1a")

        # --- Выбор категории ---
        top_frame = tk.Frame(root, bg="#1a1a1a")
        top_frame.pack(pady=(20, 5), fill="x", padx=25)
        
        tk.Label(top_frame, text="Категория:", font=("Segoe UI", 12), 
                 bg="#1a1a1a", fg="#ffffff").pack(side="left")
        
        self.category_var = tk.StringVar(value="Вагинальный секс")
        self.category_combo = ttk.Combobox(
            top_frame, textvariable=self.category_var, 
            values=list(CATEGORIES.keys()), state="readonly", 
            font=("Segoe UI", 12), width=25
        )
        self.category_combo.pack(side="left", padx=10)
        self.category_combo.bind("<<ComboboxSelected>>", self.on_category_change)

        # --- Кнопка ---
        self.btn = tk.Button(
            root, text="Показать случайную позу",
            font=("Segoe UI", 14, "bold"),
            bg="#e50914", fg="white",
            activebackground="#ff2b36", activeforeground="white",
            relief="flat", padx=20, pady=12, cursor="hand2",
            command=self.show_random, state="disabled",
        )
        self.btn.pack(pady=15)

        # --- Картинка и текст ---
        self.image_label = tk.Label(root, text="[картинка]", bg="#1a1a1a", fg="#777")
        self.image_label.pack(pady=10)
        self.title_label = tk.Label(root, text="", font=("Segoe UI", 18, "bold"),
                                    wraplength=520, bg="#1a1a1a", fg="#ffffff")
        self.title_label.pack(pady=(10, 5))
        self.desc_label = tk.Label(root, text="Загрузка...", font=("Segoe UI", 12),
                                   wraplength=520, justify="left", bg="#1a1a1a", fg="#dcdcdc")
        self.desc_label.pack(pady=10, padx=25)
        
        self.status = tk.Label(root, text="", font=("Segoe UI", 9), bg="#1a1a1a", fg="#666")
        self.status.pack(side="bottom", pady=10)

        # Первичная загрузка
        self.load_poses()

    def on_category_change(self, event=None):
        """Вызывается при смене категории в выпадающем списке."""
        category_name = self.category_var.get()
        self.current_category_url = CATEGORIES[category_name]
        self.load_poses()

    def load_poses(self):
        self.btn.config(state="disabled")
        self.desc_label.config(text="Загрузка данных с сайта...")
        self.status.config(text=f"Загрузка: {self.category_var.get()}", fg="#666")
        self.root.update_idletasks()

        try:
            self.poses = fetch_poses(self.current_category_url)
            self.status.config(text=f"Источник: medow.club · {len(self.poses)} поз", fg="#666")
            self.desc_label.config(text="Нажмите кнопку, чтобы получить случайную позу.")
            self.btn.config(text="Показать случайную позу", state="normal", command=self.show_random)
        except Exception as e:
            self.status.config(text="Ошибка загрузки", fg="#e50914")
            self.desc_label.config(text=f"Не удалось загрузить позы:\n\n{e}")
            self.btn.config(text="Повторить загрузку", state="normal", command=self.load_poses)

    def show_random(self):
        if not self.poses: return
        pose = random.choice(self.poses)
        self.title_label.config(text=pose["title"])
        self.desc_label.config(text=pose.get("description") or "Описание отсутствует.")
        
        url = pose.get("image_url")
        if url and HAS_PIL:
            self._load_image(url)
        else:
            self.image_label.config(image="", text="[картинка недоступна]")
            self._photo_ref = None

    def _load_image(self, url):
        if url in self.image_cache:
            self.image_label.config(image=self.image_cache[url], text="")
            self._photo_ref = self.image_cache[url]
            return
        self.image_label.config(image="", text="[загрузка...]")
        self.root.update_idletasks()
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content))
            img.thumbnail((500, 340))
            photo = ImageTk.PhotoImage(img)
            self.image_cache[url] = photo
            self.image_label.config(image=photo, text="")
            self._photo_ref = photo
        except Exception:
            self.image_label.config(image="", text="[не удалось загрузить картинку]")
            self._photo_ref = None

if __name__ == "__main__":
    root = tk.Tk()
    app = PoseApp(root)
    root.mainloop()
