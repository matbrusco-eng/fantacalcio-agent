import os
import requests
from bs4 import BeautifulSoup

URL_HOME = "https://www.fanta-gazzetta.it/"
URL_LOGIN_PAGE = "https://www.fanta-gazzetta.it/Account/Login"

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
    
    # Raccogliamo i campi dal form HTML
    payload_login = {}
    form = soup.find('form')
    if form:
        for input_tag in form.find_all('input'):
            name = input_tag.get('name')
            value = input_tag.get('value', '')
            if name:
                payload_login[name] = value

    payload_login["Email"] = username
    payload_login["Password"] = password

    headers_login = {
        'Referer': URL_LOGIN_PAGE,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.fanta-gazzetta.it'
    }

    print("🚀 3. POST Login...")
    resp_login = session.post(URL_LOGIN_PAGE, data=payload_login, headers=headers_login, allow_redirects=True)
    
    print(f"📡 Status Code: {resp_login.status_code}")
    print(f"🔗 URL finale post-login: {resp_login.url}")
    print("🍪 Cookie presenti:", list(session.cookies.get_dict().keys()))

    # Isoliamo i messaggi di errore restituiti dal server nell'HTML
    soup_resp = BeautifulSoup(resp_login.text, 'html.parser')
    validation_errors = soup_resp.find_all(class_=["text-danger", "validation-summary-errors", "field-validation-error"])
    
    print("\n🔍 ESITO VALIDAZIONE LOGIN:")
    if validation_errors:
        for err in validation_errors:
            txt = err.get_text(strip=True)
            if txt:
                print(f" ❌ Errore rilevato: {txt}")
    else:
        print(" ⚠️ Nessun messaggio di errore esplicito trovato nell'HTML.")

if __name__ == "__main__":
    diagnosi_login()
