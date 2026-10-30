#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎲 Random Sex Position Picker
==============================
Показывает случайную позу из категории "вагинальный секс"
(источник: https://medow.club/pozy/vid-seksa/vaginalnyj-seks).

Зависимости:
    pip install requests beautifulsoup4 Pillow

Запуск:
    python pose_picker.py
"""

import random
import sys
from io import BytesIO
from urllib.parse import urljoin

import tkinter as tk
from tkinter import messagebox

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

# ---------- настройки ----------
SOURCE_URL = "https://medow.club/pozy/vid-seksa/vaginalnyj-seks"
BASE_URL = "https://medow.club"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}


# ---------- парсер ----------
def fetch_poses():
    """Собирает позы с сайта. Возвращает список dict или кидает исключение."""
    r = requests.get(SOURCE_URL, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    poses, seen = [], set()

    # Основной вариант: карточки-статьи со ссылкой на полную позу
    candidates = soup.select("article, .post, .entry, .position, .item, .card")
    if not candidates:
        # Резервный вариант: все ссылки, ведущие на /pozy/
        candidates = soup.find_all("a", href=lambda h: h and "/pozy/" in h)

    for block in candidates:
        link_tag = block if block.name == "a" else block.find("a", href=True)
        if not link_tag:
            continue

        href = link_tag.get("href", "")
        if "/pozy/" not in href:
            continue

        title = link_tag.get_text(strip=True)
        if not title or len(title) < 3 or title in seen:
            continue
        seen.add(title)

        desc_tag = block.find("p") if block.name != "a" else None
        desc = desc_tag.get_text(strip=True) if desc_tag else ""

        img_tag = block.find("img") if block.name != "a" else None
        img_url = None
        if img_tag:
            src = (
                img_tag.get("src")
                or img_tag.get("data-src")
                or img_tag.get("data-lazy-src")
                or img_tag.get("data-original")
            )
            if src:
                img_url = urljoin(BASE_URL, src)

        poses.append({
            "title": title,
            "description": desc,
            "image_url": img_url,
            "page_url": urljoin(BASE_URL, href),
        })

    if not poses:
        raise RuntimeError(
            "Не удалось найти позы на сайте. "
            "Возможно, изменилась вёрстка или сайт требует JS-рендеринг."
        )
    return poses


# ---------- GUI ----------
class PoseApp:
    def __init__(self, root):
        self.root = root
        self.poses = []
        self.image_cache = {}
        self._photo_ref = None

        root.title("Случайная поза")
        root.geometry("580x780")
        root.minsize(400, 500)
        root.configure(bg="#1a1a1a")

        tk.Label(root, text="🎲 Случайная поза",
                 font=("Segoe UI", 22, "bold"),
                 bg="#1a1a1a", fg="#ffffff").pack(pady=(20, 5))

        self.btn = tk.Button(
            root, text="Показать случайную позу",
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
                                    wraplength=520, bg="#1a1a1a", fg="#ffffff")
        self.title_label.pack(pady=(10, 5))

        self.desc_label = tk.Label(
            root,
            text="Загрузка поз с сайта...",
            font=("Segoe UI", 12), wraplength=520, justify="left",
            bg="#1a1a1a", fg="#dcdcdc",
        )
        self.desc_label.pack(pady=10, padx=25)

        self.status = tk.Label(root, text="Загрузка...",
                               font=("Segoe UI", 9), bg="#1a1a1a", fg="#666")
        self.status.pack(side="bottom", pady=10)

        # грузим позы в фоне
        root.after(100, self.load_poses)

    def load_poses(self):
        try:
            self.poses = fetch_poses()
        except Exception as e:
            self.status.config(text="Ошибка загрузки", fg="#e50914")
            self.desc_label.config(
                text=f"Не удалось загрузить позы с сайта:\n\n{e}\n\n"
                     "Проверьте интернет-соединение и нажмите кнопку ниже."
            )
            self.btn.config(text="Повторить загрузку", state="normal",
                            command=self.retry_load)
            return

        self.status.config(text=f"Источник: medow.club · {len(self.poses)} поз", fg="#666")
        self.desc_label.config(text="Нажмите кнопку, чтобы получить случайную позу.")
        self.btn.config(text="Показать случайную позу", state="normal",
                        command=self.show_random)

    def retry_load(self):
        self.btn.config(state="disabled")
        self.desc_label.config(text="Повторная загрузка...")
        self.status.config(text="Загрузка...", fg="#666")
        self.root.after(100, self.load_poses)

    def show_random(self):
        if not self.poses:
            return
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
            img.thumbnail((500, 340))
            photo = ImageTk.PhotoImage(img)
            self.image_cache[url] = photo
            self.image_label.config(image=photo, text="")
            self._photo_ref = photo
        except Exception:
            self.image_label.config(image="", text="[не удалось загрузить картинку]")
            self._photo_ref = None


# ---------- main ----------
def main():
    root = tk.Tk()
    PoseApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
