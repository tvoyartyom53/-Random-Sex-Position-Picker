#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎲 Random Sex Position Picker
Зависимости: pip install requests beautifulsoup4 Pillow
Запуск:      python pose_picker.py
"""

import random
import traceback
from io import BytesIO
from urllib.parse import urljoin

import tkinter as tk
from tkinter import scrolledtext

# ---------- зависимости ----------
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

# ---------- настройки ----------
SOURCE_URL = "https://medow.club/pozy/vid-seksa/vaginalnyj-seks/"
BASE_URL = "https://medow.club"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://medow.club/",
}


# ---------- парсер с несколькими стратегиями ----------
def fetch_poses(log):
    """Пробует несколько стратегий парсинга, пока не найдёт позы."""
    log(f"GET {SOURCE_URL}")
    session = requests.Session()
    session.headers.update(HEADERS)

    r = session.get(SOURCE_URL, timeout=20)
    log(f"HTTP {r.status_code}, {len(r.text)} байт")
    r.raise_for_status()
    if r.status_code != 200:
        raise RuntimeError(f"Сайт вернул HTTP {r.status_code}")

    soup = BeautifulSoup(r.text, "html.parser")
    log(f"<title>: {soup.title.string.strip() if soup.title and soup.title.string else 'НЕТ'}")

    strategies = [
        ("div.post-card",        "div.post-card__title a",
                                 "div.post-card__thumbnail img",
                                 "div.post-card__description"),
        ("article",              "h2 a, h3 a, a[href*='/pozy/']",
                                 "img",
                                 "p"),
        (".card, .item, .entry", "a[href*='/pozy/']",
                                 "img",
                                 "p"),
    ]

    for container_sel, title_sel, img_sel, desc_sel in strategies:
        cards = soup.select(container_sel)
        log(f"Стратегия '{container_sel}': найдено {len(cards)} блоков")
        poses, seen = [], set()

        for card in cards:
            a = card.select_one(title_sel) if title_sel else None
            if not a:
                continue
            href = a.get("href", "")
            if "/pozy/" not in href or href.rstrip("/") == SOURCE_URL.rstrip("/"):
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 3 or title in seen:
                continue
            seen.add(title)

            img_url = None
            img_tag = card.select_one(img_sel) if img_sel else None
            if img_tag:
                src = (img_tag.get("src") or img_tag.get("data-src")
                       or img_tag.get("data-lazy-src") or img_tag.get("data-original"))
                if src and not src.startswith("data:"):
                    img_url = urljoin(BASE_URL, src)

            desc = ""
            dtag = card.select_one(desc_sel) if desc_sel else None
            if dtag:
                desc = dtag.get_text(strip=True)

            poses.append({
                "title": title,
                "description": desc,
                "image_url": img_url,
                "page_url": urljoin(BASE_URL, href),
            })

        if poses:
            log(f"✅ Стратегия сработала, извлечено {len(poses)} поз")
            return poses

    # Последняя стратегия — вообще без контейнера, только ссылки
    log("Fallback: собираю все ссылки с /pozy/ на странице")
    poses, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/pozy/" not in href or href.rstrip("/") == SOURCE_URL.rstrip("/"):
            continue
        title = a.get_text(strip=True)
        if not title or len(title) < 3 or title in seen:
            continue
        seen.add(title)

        img_tag = a.find("img") or (a.parent.find("img") if a.parent else None)
        img_url = None
        if img_tag:
            src = (img_tag.get("src") or img_tag.get("data-src")
                   or img_tag.get("data-lazy-src"))
            if src and not src.startswith("data:"):
                img_url = urljoin(BASE_URL, src)

        poses.append({
            "title": title,
            "description": "",
            "image_url": img_url,
            "page_url": urljoin(BASE_URL, href),
        })

    log(f"Найдено по ссылкам: {len(poses)}")
    if not poses:
        raise RuntimeError(
            "Не удалось найти ни одной позы на странице. "
            "Сайт, скорее всего, рендерит контент через JavaScript — "
            "нужен Playwright/Selenium."
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
        root.geometry("620x840")
        root.minsize(460, 620)
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
                                    wraplength=560, bg="#1a1a1a", fg="#ffffff")
        self.title_label.pack(pady=(10, 5))

        self.desc_label = tk.Label(
            root, text="Загрузка поз с сайта...",
            font=("Segoe UI", 12), wraplength=560, justify="left",
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
            self.desc_label.config(
                text=f"Не хватает зависимостей: {', '.join(_missing)}\n\n"
                     f"Откройте терминал и выполните:\n"
                     f"pip install requests beautifulsoup4 Pillow",
                fg="#e50914",
            )
            self.btn.config(text="Выход", state="normal",
                            command=self.root.destroy)
            return

        root.after(200, self.load_poses)

    def log(self, msg):
        try:
            print(msg)
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.root.update_idletasks()
        except Exception:
            pass

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

        self.desc_label.config(
            text=f"Загружено {len(self.poses)} поз.\n"
                 f"Нажмите кнопку, чтобы получить случайную.",
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
            img.thumbnail((540, 350))
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
