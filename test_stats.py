import requests

def recupera_fantamedia_test(player_code):
    url_api = f"https://www.fantacalcio.it/api/v1/giocatori/{player_code}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    response = requests.get(url_api, headers=headers)
    
    print(f"📡 Status Code: {response.status_code}")
    print(f"📄 Lunghezza risposta: {len(response.text)} caratteri")
    print("📝 Anteprima contenuto (primi 300 char):")
    print(response.text[:300].replace('\n', ' '))

if __name__ == "__main__":
    recupera_fantamedia_test("2194")
