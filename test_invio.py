import os
import requests
from bs4 import BeautifulSoup

URL_HOME = "https://www.fanta-gazzetta.it/"
URL_LOGIN_PAGE = "https://www.fanta-gazzetta.it/Account/Login"
URL_FORMAZIONE = "https://www.fanta-gazzetta.it/api/CoachCurrentTeams/InvioFormazione"

def diagnosi_login():
    username = os.environ.get("FANTA_USER")
    password = os.environ.get("FANTA_PASS")
    
    if not username or not password:
        print("❌ Errore: FANTA_USER o FANTA_PASS non impostati nei Secrets.")
        return

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
    })

    print("🌐 1. GET Home Page...")
    session.get(URL_HOME)

    print("🔑 2. GET Login Page...")
    resp_login_page = session.get(URL_LOGIN_PAGE)
    soup = BeautifulSoup(resp_login_page.text, 'html.parser')
    
    # Raccogliamo TUTTI i campi nascosti presenti nel form di login originale
    payload_login = {}
    form = soup.find('form')
    if form:
        for input_tag in form.find_all('input'):
            name = input_tag.get('name')
            value = input_tag.get('value', '')
            if name:
                payload_login[name] = value

    # Sovrascriviamo le credenziali
    payload_login["Email"] = username
    payload_login["Password"] = password
    payload_login["RememberMe"] = "false"

    print("📦 Payload inviato al Login:", {k: (v if k != 'Password' else '***') for k, v in payload_login.items()})

    headers_login = {
        'Referer': URL_LOGIN_PAGE,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.fanta-gazzetta.it'
    }

    print("🚀 3. POST Login standard (senza AJAX header)...")
    resp_login = session.post(URL_LOGIN_PAGE, data=payload_login, headers=headers_login, allow_redirects=True)
    
    print(f"📡 Status Code: {resp_login.status_code}")
    print(f"🔗 URL finale post-login: {resp_login.url}")
    print("🍪 Cookie presenti:", list(session.cookies.get_dict().keys()))
    print("📄 Anteprima risposta login (primi 300 char):")
    print(resp_login.text[:300].replace('\n', ' '))

if __name__ == "__main__":
    diagnosi_login()
