import requests
from bs4 import BeautifulSoup
import time
import json
import os

# ====== CONFIGURATION ======
TELEGRAM_TOKEN = "8602097394:AAHmfgauUaLHFM5F5xF9b9AxhxZw7PwSw4E"
CHAT_ID = "7547692358"
MIN_YEAR = 2021
MAX_PRICE = 25000
CHECK_INTERVAL = 900  # 15 minutes
SEEN_FILE = "seen_ads.json"
# ===========================

ELECTRIC_BRANDS = [
    # Européennes
    "bmw", "audi", "volkswagen", "mercedes-benz", "renault", "peugeot",
    "citroen", "opel", "fiat", "volvo", "polestar", "skoda", "seat",
    "cupra", "mini", "porsche", "smart",
    # Asiatiques
    "toyota", "nissan", "hyundai", "kia", "honda", "mazda", "mitsubishi",
    "subaru", "byd", "mg", "nio", "xpeng", "ora", "aiways", "zeekr",
    "lynk-co",
    # Américaines
    "rivian", "lucid", "fisker"
]

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
    """Extrait le prix numérique depuis une chaîne comme '€ 12.500'"""
    try:
        clean = text.replace("€", "").replace(".", "").replace(",", "").strip()
        return int(''.join(filter(str.isdigit, clean)))
    except:
        return None

def scrape_brand(brand):
    ads = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for page in range(2):  # page 0 et page 1
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

                # Extract year
                year = None
                for img in link.find_all("img"):
                    alt = img.get("alt", "")
                    if "ERD:" in alt:
                        try:
                            year = int(alt.replace("ERD:", "").strip())
                        except:
                            pass

                if year is None or year < MIN_YEAR:
                    continue

                # Extract title
                h2 = link.find("h2")
                title = h2.get_text(strip=True) if h2 else brand.upper()

                # Extract subtitle
                p = link.find("p")
                subtitle = p.get_text(strip=True) if p else ""

                # Extract price
                price_raw = "N/A"
                price_num = None
                for text in link.stripped_strings:
                    if "€" in text:
                        price_raw = text.strip()
                        price_num = extract_price(text)
                        break

                # Filter by price
                if price_num is not None and price_num > MAX_PRICE:
                    continue

                # Extract mileage
                km = "N/A"
                for img in link.find_all("img"):
                    alt = img.get("alt", "")
                    src = img.get("src", "")
                    if "distance" in src:
                        km = alt
                        break

                ads.append({
                    "url": full_url,
                    "title": title,
                    "subtitle": subtitle,
                    "year": year,
                    "price": price_raw,
                    "km": km,
                    "brand": brand
                })

        except Exception as e:
            print(f"Erreur {brand} page {page}: {e}")

    return ads

def scrape_all():
    all_ads = []
    seen_urls = set()
    
    for brand in ELECTRIC_BRANDS:
        print(f"🔍 Scraping {brand}...")
        ads = scrape_brand(brand)
        for ad in ads:
            if ad["url"] not in seen_urls:
                seen_urls.add(ad["url"])
                all_ads.append(ad)
        time.sleep(1)  # Pause pour ne pas surcharger le serveur
    
    return all_ads

def main():
    print("⚡ Electric Car Alert Bot démarré !")
    send_telegram(
        "⚡ <b>Electric Car Alert Bot démarré !</b>\n"
        "Je surveille schadeautos.nl pour toutes les voitures électriques 2021+\n"
        "Prix max : 25.000€ — toutes les 15 minutes."
    )

    seen = load_seen()
    print(f"Annonces déjà vues: {len(seen)}")

    while True:
        try:
            print(f"\n🔍 Vérification... {time.strftime('%H:%M:%S')}")
            ads = scrape_all()
            print(f"Total annonces trouvées: {len(ads)}")

            new_ads = [ad for ad in ads if ad["url"] not in seen]
            print(f"Nouvelles annonces: {len(new_ads)}")

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
                print(f"✅ Envoyé: {ad['title']} {ad['year']}")

            save_seen(seen)

            if not new_ads:
                print("Aucune nouvelle annonce.")

        except Exception as e:
            print(f"Erreur boucle principale: {e}")

        print(f"⏳ Attente {CHECK_INTERVAL//60} minutes...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
