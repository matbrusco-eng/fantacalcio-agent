import requests

def recupera_fantamedia_test(player_code):
    # Fantacalcio.it usa spesso endpoint JSON dedicati per le statistiche dei giocatori
    url_api = f"https://www.fantacalcio.it/api/v1/giocatori/{player_code}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    
    response = requests.get(url_api, headers=headers)
    
    print(f"📡 Status Code per codice {player_code}: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("📊 Dati ricevuti:", data)
    else:
        print("⚠️ API diretta non disponibile. Passiamo allo scraping della tabella statistiche generali.")

if __name__ == "__main__":
    # Testiamo con il codice di Calhanoglu (2194) o De Bruyne (2517)
    recupera_fantamedia_test("2194")
