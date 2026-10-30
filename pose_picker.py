#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎲 Random Sex Position Picker
Показывает случайную позу с сайта medow.club.
Зависимости: pip install requests beautifulsoup4 Pillow
Запуск:      python pose_picker.py
"""

import random
import traceback
from io import BytesIO
from urllib.parse import urljoin

import tkinter as tk
from tkinter import scrolledtext

# ---------- Проверка зависимостей ----------
_missing = []
try:
    import requests
except ImportError:
    _missing.append("requests")
try:
    from bs4 import BeautifulSoup
except ImportError:
    _missing.append("beautifulsoup4")
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    _missing.append("Pillow")

# ---------- Настройки ----------
SOURCE_URL = "https://medow.club/pozy/vid-seksa/vaginalnyj-seks/"
BASE_URL = "https://medow.club"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ---------- Парсер (ТОЧНЫЕ СЕЛЕКТОРЫ) ----------
def fetch_poses(log):
    """Собирает позы с сайта, используя точные CSS-классы."""
    log(f"Запрос: {SOURCE_URL}")
    session = requests.Session()
    session.headers.update(HEADERS)
    r = session.get(SOURCE_URL, timeout=20)
    log(f"HTTP статус: {r.status_code}, размер: {len(r.text)} байт")
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    log(f"Заголовок страницы: {soup.title.string if soup.title else 'НЕТ'}")

    poses = []
    # Находим все карточки с позами
    cards = soup.select("div.post-card")
    log(f"Найдено карточек (div.post-card): {len(cards)}")

    if not cards:
        raise RuntimeError(
            "На странице не найдено ни одной карточки с позой (div.post-card). "
            "Возможно, сайт изменил вёрстку."
        )

    for card in cards:
        # 1. Заголовок и ссылка на страницу позы
        title_div = card.select_one("div.post-card__title")
        link_tag = title_div.find("a") if title_div else None
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        page_url = urljoin(BASE_URL, link_tag.get("href", ""))

        # 2. Картинка
        img_tag = card.select_one("div.post-card__thumbnail img")
        img_url = None
        if img_tag:
            src = img_tag.get("src")
            if src:
                img_url = urljoin(BASE_URL, src)

        # 3. Описание
        desc_div = card.select_one("div.post-card__description")
        description = desc_div.get_text(strip=True) if desc_div else ""

        poses.append({
            "title": title,
            "description": description,
            "image_url": img_url,
            "page_url": page_url,
        })

    log(f"Успешно извлечено поз: {len(poses)}")
    return poses

# ---------- GUI ----------
class PoseApp:
    def __init__(self, root):
        self.root = root
        self.poses = []
        self.image_cache = {}
        self._photo_ref = None

        root.title("Случайная поза")
        root.geometry("600x820")
        root.minsize(450, 600)
        root.configure(bg="#1a1a1a")

        tk.Label(root, text="🎲 Случайная поза",
                 font=("Segoe UI", 22, "bold"),
                 bg="#1a1a1a", fg="#ffffff").pack(pady=(20, 5))

        self.btn = tk.Button(
            root, text="Загрузка...",
            font=("Segoe UI", 14, "bold"),
            bg="#e50914", fg="white",
            activebackground="#ff2b36", activeforeground="white",
            relief="flat", padx=20, pady=12, cursor="hand2",
            command=self.show_random, state="disabled",
        )
        self.btn.pack(pady=15)

        self.image_label = tk.Label(root, text="[картинка]",
                                    bg="#1a1a1a", fg="#777",
                                    font=("Segoe UI", 10))
        self.image_label.pack(pady=10)

        self.title_label = tk.Label(root, text="",
                                    font=("Segoe UI", 18, "bold"),
                                    wraplength=540, bg="#1a1a1a", fg="#ffffff")
        self.title_label.pack(pady=(10, 5))

        self.desc_label = tk.Label(
            root, text="Загрузка поз с сайта...",
            font=("Segoe UI", 12), wraplength=540, justify="left",
            bg="#1a1a1a", fg="#dcdcdc",
        )
        self.desc_label.pack(pady=10, padx=25)

        self.log_box = scrolledtext.ScrolledText(
            root, height=6, font=("Consolas", 9),
            bg="#0f0f0f", fg="#9f9f9f", relief="flat",
        )
        self.log_box.pack(fill="x", padx=15, pady=(10, 5))

        if _missing:
            self.log(f"❌ Не установлены модули: {', '.join(_missing)}")
            self.log("Выполните в терминале:")
            self.log("    pip install requests beautifulsoup4 Pillow")
            self.desc_label.config(
                text=f"Не хватает зависимостей: {', '.join(_missing)}\n"
                     f"Откройте терминал и выполните:\n"
                     f"pip install requests beautifulsoup4 Pillow",
                fg="#e50914",
            )
            self.btn.config(text="Выход", state="normal",
                            command=self.root.destroy)
            return

        root.after(200, self.load_poses)

    def log(self, msg):
        print(msg)
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.root.update_idletasks()

    def load_poses(self):
        try:
            self.log("--- Загрузка ---")
            self.poses = fetch_poses(self.log)
        except Exception as e:
            self.log(f"❌ ОШИБКА: {e}")
            self.log(traceback.format_exc())
            self.desc_label.config(
                text=f"Не удалось загрузить позы:\n\n{e}",
                fg="#e50914",
            )
            self.btn.config(text="Повторить загрузку", state="normal",
                            command=self.retry_load)
            return

        self.log(f"✅ Успешно загружено {len(self.poses)} поз")
        self.desc_label.config(
            text="Нажмите кнопку, чтобы получить случайную позу.",
            fg="#dcdcdc",
        )
        self.btn.config(text="Показать случайную позу", state="normal",
                        command=self.show_random)

    def retry_load(self):
        self.btn.config(state="disabled", text="Загрузка...")
        self.root.after(100, self.load_poses)

    def show_random(self):
        if not self.poses:
            return
        pose = random.choice(self.poses)
        self.title_label.config(text=pose["title"])
        self.desc_label.config(
            text=pose.get("description") or "Описание отсутствует.",
            fg="#dcdcdc",
        )
        url = pose.get("image_url")
        if url and HAS_PIL:
            self._load_image(url)
        else:
            self.image_label.config(image="", text="[картинка недоступна]")
            self._photo_ref = None

    def _load_image(self, url):
        if url in self.image_cache:
            photo = self.image_cache[url]
            self.image_label.config(image=photo, text="")
            self._photo_ref = photo
            return
        self.image_label.config(image="", text="[загрузка...]")
        self.root.update_idletasks()
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content))
            img.thumbnail((520, 340))
            photo = ImageTk.PhotoImage(img)
            self.image_cache[url] = photo
            self.image_label.config(image=photo, text="")
            self._photo_ref = photo
        except Exception as e:
            self.log(f"⚠ картинка не загрузилась: {e}")
            self.image_label.config(image="", text="[не удалось загрузить картинку]")
            self._photo_ref = None

# ---------- main ----------
def main():
    root = tk.Tk()
    PoseApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
