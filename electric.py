import requests
from bs4 import BeautifulSoup
import time
import json
import os

TELEGRAM_TOKEN = "8602097394:AAHmfgauUaLHFM5F5xF9b9AxhxZw7PwSw4E"
CHAT_ID = "7547692358"
MIN_YEAR = 2021
MAX_PRICE = 25000
CHECK_INTERVAL = 900
SEEN_FILE = "seen_electric.json"

# ===== MARQUES 100% ÉLECTRIQUES =====
PURE_ELECTRIC_BRANDS = [
    "tesla", "byd", "polestar", "nio", "xpeng", "zeekr", "ora",
    "aiways", "lynk-co", "rivian", "lucid", "vinfast", "leapmotor",
    "smart", "genesis", "voyah", "hongqi"
]

# ===== MARQUES MIXTES + MODÈLES BEV UNIQUEMENT =====
MIXED_BRANDS_KEYWORDS = {
    "bmw": ["i3", "i4", "i5", "i7", "ix1", "ix2", "ix3", "ix "],
    "audi": ["e-tron", "etron", "q4 e-tron", "q5 e-tron", "q6 e-tron", "q8 e-tron", "a6 e-tron", "a5 e-tron"],
    "volkswagen": ["id.1", "id.2", "id.3", "id.4", "id.5", "id.6", "id.7", "id. polo", "id polo", "e-golf", "e-up"],
    "mercedes-benz": ["eqa", "eqb", "eqc", "eqe", "eqs", "cla electric", "cla 250", "glc electric", "g electric"],
    "renault": ["zoe", "renault 5", "renault 4", "megane e-tech", "scenic e-tech", "twingo electric", "kangoo e-tech"],
    "peugeot": ["e-208", "e-2008", "e-308", "e-3008", "e-5008", "e-408", "e-rifter", "e-partner"],
    "citroen": ["e-c3", "e-c4", "ec4", "e-berlingo", "e-spacetourer", "e-jumpy", "c3 aircross electric", "ec3"],
    "opel": ["corsa-e", "corsa electric", "mokka-e", "mokka electric", "astra electric", "grandland electric", "frontera electric", "combo-e", "vivaro-e", "zafira electric"],
    "fiat": ["500e", "500 electric", "600e", "600 electric", "grande panda electric", "panda electric"],
    "volvo": ["ex30", "ex40", "ex60", "ex90", "ec40", "xc40 recharge", "c40 recharge"],
    "skoda": ["enyaq", "elroq", "epiq"],
    "seat": ["mii electric", "born"],
    "cupra": ["born", "tavascan", "raval"],
    "mini": ["mini electric", "cooper se", "countryman electric", "aceman"],
    "porsche": ["taycan", "macan electric"],
    "hyundai": ["ioniq 5", "ioniq 6", "ioniq 9", "kona electric", "kona ev", "nexo"],
    "kia": ["ev3", "ev5", "ev6", "ev9", "niro ev", "soul ev", "e-niro"],
    "nissan": ["leaf", "ariya"],
    "toyota": ["bz4x", "bz3", "urban cruiser electric", "c-hr electric", "bz compact"],
    "honda": ["honda e", "e:ny1", "eny1", "e:np1", "zr-v electric"],
    "mazda": ["mx-30", "mazda 6e", "6e"],
    "mg": ["mg4", "mg5", "zs ev", "marvel r", "cyberster", "mg3 electric"],
    "ford": ["mustang mach-e", "mach-e", "explorer electric", "capri electric"],
    "dacia": ["spring"],
    "ds": ["ds 3 electric", "ds3 electric", "ds 4 electric"],
    "alfa-romeo": ["junior electric", "milano electric"],
    "jeep": ["avenger electric"],
    "lancia": ["ypsilon electric"],
    "jaguar": ["i-pace", "ipace", "i pace", "ev400"],
    "subaru": ["solterra"],
    "lexus": ["uz electric", "rz ", "lbx electric"],
    "genesis": ["gv60", "gv70 electric", "g80 electric"],
}

BASE_URL = "https://www.schadeautos.nl/en/damaged-car"

def load_seen():
    try:
        if os.path.exists(SEEN_FILE):
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
    except:
        pass
    return set()

def save_seen(seen):
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(seen), f)
    except Exception as e:
        print(f"Erreur sauvegarde: {e}")

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }, timeout=10)
        print(f"Telegram: {resp.status_code}")
    except Exception as e:
        print(f"Erreur Telegram: {e}")

def extract_price(text):
    try:
        clean = text.replace("€", "").replace(".", "").replace(",", "").strip()
        return int(''.join(filter(str.isdigit, clean)))
    except:
        return None

def is_electric_model(title, subtitle, keywords):
    combined = (title + " " + subtitle).lower()
    return any(kw.lower() in combined for kw in keywords)

def scrape_brand(brand, keywords=None):
    ads = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    seen_urls = set()

    for page in range(2):
        url = f"{BASE_URL}/{brand}" if page == 0 else f"{BASE_URL}/{brand}/{page}"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.find_all("a", href=lambda h: h and "/en/damaged/passenger-cars/" in h)

            for link in links:
                href = link.get("href", "")
                if not href:
                    continue
                full_url = "https://www.schadeautos.nl" + href if href.startswith("/") else href
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # Extract year
                year = None
                for img in link.find_all("img"):
                    alt = img.get("alt", "")
                    if "ERD:" in alt:
                        try:
                            year = int(alt.replace("ERD:", "").strip())
                        except:
                            pass

                if year is not None and year < MIN_YEAR:
                    continue

                # Extract title & subtitle
                h2 = link.find("h2")
                title = h2.get_text(strip=True) if h2 else brand.upper()
                p = link.find("p")
                subtitle = p.get_text(strip=True) if p else ""

                # Filtre modèle pour marques mixtes
                if keywords and not is_electric_model(title, subtitle, keywords):
                    continue

                # Extract price
                price_raw = "N/A"
                price_num = None
                for text in link.stripped_strings:
                    if "€" in text:
                        price_raw = text.strip()
                        price_num = extract_price(text)
                        break

                if price_num is not None and price_num > MAX_PRICE:
                    continue

                # Extract mileage
                km = "N/A"
                for img in link.find_all("img"):
                    if "distance" in img.get("src", ""):
                        km = img.get("alt", "N/A")
                        break

                ads.append({
                    "url": full_url,
                    "title": title,
                    "subtitle": subtitle,
                    "year": str(year) if year else "?",
                    "price": price_raw,
                    "km": km
                })

        except Exception as e:
            print(f"Erreur {brand}: {e}")

    return ads

def scrape_all():
    all_ads = []
    seen_urls = set()

    for brand in PURE_ELECTRIC_BRANDS:
        print(f"⚡ {brand}...")
        for ad in scrape_brand(brand, keywords=None):
            if ad["url"] not in seen_urls:
                seen_urls.add(ad["url"])
                all_ads.append(ad)
        time.sleep(0.5)

    for brand, keywords in MIXED_BRANDS_KEYWORDS.items():
        print(f"🔍 {brand}...")
        for ad in scrape_brand(brand, keywords=keywords):
            if ad["url"] not in seen_urls:
                seen_urls.add(ad["url"])
                all_ads.append(ad)
        time.sleep(0.5)

    return all_ads

def main():
    print("⚡ Electric Car Alert Bot démarré !")
    seen = load_seen()

    # Premier démarrage : mémorise tout sans envoyer
    if len(seen) == 0:
        print("🔄 Mémorisation des annonces existantes (sans notification)...")
        ads = scrape_all()
        for ad in ads:
            seen.add(ad["url"])
        save_seen(seen)
        print(f"✅ {len(seen)} annonces existantes mémorisées.")
        send_telegram(
            f"⚡ <b>Electric Car Alert Bot démarré !</b>\n"
            f"✅ {len(seen)} annonces existantes ignorées.\n"
            f"📡 Surveillance active : voitures 100% électriques 2021+ sous 25.000€\n"
            f"⏱ Vérification toutes les 15 minutes."
        )
    else:
        print(f"Annonces mémorisées: {len(seen)}")
        send_telegram("⚡ <b>Electric Car Alert Bot redémarré !</b>\nSurveillance des nouvelles annonces en cours.")

    while True:
        try:
            print(f"\n⚡ Vérification... {time.strftime('%H:%M:%S')}")
            ads = scrape_all()
            new_ads = [ad for ad in ads if ad["url"] not in seen]
            print(f"Nouvelles: {len(new_ads)}")

            for ad in new_ads:
                msg = (
                    f"⚡ <b>NOUVELLE VOITURE ÉLECTRIQUE !</b>\n\n"
                    f"📌 <b>{ad['title']}</b>\n"
                    f"🔹 {ad['subtitle']}\n"
                    f"📅 Année : {ad['year']}\n"
                    f"💶 Prix : {ad['price']}\n"
                    f"🛣 KM : {ad['km']}\n\n"
                    f"🔗 <a href='{ad['url']}'>Voir l'annonce</a>"
                )
                send_telegram(msg)
                seen.add(ad["url"])
                print(f"✅ {ad['title']} {ad['year']}")

            save_seen(seen)
            if not new_ads:
                print("Aucune nouvelle annonce.")

        except Exception as e:
            print(f"Erreur: {e}")

        print(f"⏳ Attente 15 min...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
