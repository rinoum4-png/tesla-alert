import requests
from bs4 import BeautifulSoup
import time
import json
import os

TELEGRAM_TOKEN = "8602097394:AAHmfgauUaLHFM5F5xF9b9AxhxZw7PwSw4E"
CHAT_ID = "7547692358"
MIN_YEAR = 2021
CHECK_INTERVAL = 900
SEEN_FILE = "seen_tesla.json"

URLS = [
    "https://www.schadeautos.nl/en/damaged-car/tesla/model-y",
    "https://www.schadeautos.nl/en/damaged-car/tesla/model-3",
    "https://www.schadeautos.nl/en/damaged-car/tesla/model-x",
    "https://www.schadeautos.nl/en/damaged-car/tesla/model-s",
    "https://www.schadeautos.nl/en/damaged-car/tesla/model-y/1",
    "https://www.schadeautos.nl/en/damaged-car/tesla/model-3/1",
    "https://www.schadeautos.nl/en/damaged-car/tesla/model-x/1",
    "https://www.schadeautos.nl/en/damaged-car/tesla/model-s/1",
]

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

def scrape_tesla_ads():
    ads = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    seen_urls = set()

    for url in URLS:
        try:
            print(f"Scraping: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.find_all("a", href=lambda h: h and "/en/damaged/passenger-cars/tesla" in h)
            print(f"  Trouvé {len(links)} annonces")

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

                # Extract title
                h2 = link.find("h2")
                title = h2.get_text(strip=True) if h2 else "Tesla"
                p = link.find("p")
                subtitle = p.get_text(strip=True) if p else ""

                # Extract price
                price = "N/A"
                for text in link.stripped_strings:
                    if "€" in text:
                        price = text.strip()
                        break

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
                    "price": price,
                    "km": km
                })

        except Exception as e:
            print(f"Erreur scraping {url}: {e}")

    return ads

def main():
    print("🚀 Tesla Alert Bot démarré !")
    seen = load_seen()

    # Premier démarrage : mémorise tout sans envoyer
    if len(seen) == 0:
        print("🔄 Mémorisation des annonces existantes (sans notification)...")
        ads = scrape_tesla_ads()
        for ad in ads:
            seen.add(ad["url"])
        save_seen(seen)
        print(f"✅ {len(seen)} annonces existantes mémorisées.")
        send_telegram(
            f"🚀 <b>Tesla Alert Bot démarré !</b>\n"
            f"✅ {len(seen)} annonces existantes ignorées.\n"
            f"📡 Surveillance active : Tesla Model Y, 3, X, S — 2021+\n"
            f"⏱ Vérification toutes les 15 minutes."
        )
    else:
        print(f"Annonces mémorisées: {len(seen)}")
        send_telegram("🚀 <b>Tesla Alert Bot redémarré !</b>\nSurveillance des nouvelles annonces Tesla en cours.")

    while True:
        try:
            print(f"\n🔍 Vérification... {time.strftime('%H:%M:%S')}")
            ads = scrape_tesla_ads()
            new_ads = [ad for ad in ads if ad["url"] not in seen]
            print(f"Nouvelles: {len(new_ads)}")

            for ad in new_ads:
                msg = (
                    f"🚨 <b>NOUVELLE TESLA !</b>\n\n"
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

