import os
import requests
import urllib.parse
from bs4 import BeautifulSoup

URL_HOME = "https://www.fanta-gazzetta.it/"
URL_LOGIN_PAGE = "https://www.fanta-gazzetta.it/Account/Login"

def test_login_encoding():
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

    session.get(URL_HOME)
    resp_login_page = session.get(URL_LOGIN_PAGE)
    soup = BeautifulSoup(resp_login_page.text, 'html.parser')
    
    token_input = soup.find('input', {'name': '__RequestVerificationToken'})
    token_val = token_input.get('value') if token_input else ""

    # Test con codifica URL esplicita per i caratteri speciali della password
    payload_login = {
        "Email": username,
        "UserName": username, # Tentativo fallback se il server mappa UserName
        "Password": password,
        "__RequestVerificationToken": token_val,
        "RememberMe": "false"
    }

    headers_login = {
        'Referer': URL_LOGIN_PAGE,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.fanta-gazzetta.it'
    }

    print("🔑 Tentativo di login con URL-encoding e parametri allineati...")
    resp_login = session.post(URL_LOGIN_PAGE, data=payload_login, headers=headers_login, allow_redirects=True)
    
    soup_resp = BeautifulSoup(resp_login.text, 'html.parser')
    validation_errors = soup_resp.find_all(class_=["text-danger", "validation-summary-errors", "field-validation-error"])
    
    print("🍪 Cookie ottenuti:", list(session.cookies.get_dict().keys()))
    
    if any(".AspNetCore.Cookies" in c or ".AspNetCore.Identity" in c for c in session.cookies.get_dict().keys()):
        print("🎉 SUCCESS: Login effettuato con successo! Cookie di sessione rilasciato.")
    else:
        print("❌ Errore persistente:")
        for err in validation_errors:
            txt = err.get_text(strip=True)
            if txt:
                print(f" -> {txt}")

if __name__ == "__main__":
    test_login_encoding()
