import os
import requests
from bs4 import BeautifulSoup

URL_HOME = "https://www.fanta-gazzetta.it/"
URL_LOGIN_PAGE = "https://www.fanta-gazzetta.it/Account/Login"
URL_FORMAZIONE = "https://www.fanta-gazzetta.it/api/CoachCurrentTeams/InvioFormazione"
URL_SAVE = "https://www.fanta-gazzetta.it/api/CoachCurrentTeams/Save"

def test_salva_formazione_fissa():
    username = os.environ.get("FANTA_USER")
    password = os.environ.get("FANTA_PASS")
    
    if not username or not password:
        print("❌ Errore: FANTA_USER o FANTA_PASS non impostati nei Secrets di GitHub.")
        return

    session = requests.Session()
    
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
    })

    # 1. Visita alla HOME PAGE per innescare la sessione base ASP.NET
    print("🌐 1. Inizializzazione sessione sulla Home Page...")
    session.get(URL_HOME)

    # 2. Visita alla pagina di Login per estrarre il token Anti-Forgery
    print("🔑 2. Connessione alla pagina di login...")
    resp_login_page = session.get(URL_LOGIN_PAGE)
    if resp_login_page.status_code != 200:
        print(f"❌ Impossibile raggiungere il login. Status: {resp_login_page.status_code}")
        return

    soup = BeautifulSoup(resp_login_page.text, 'html.parser')
    token_input = soup.find('input', {'name': '__RequestVerificationToken'})
    token_val = token_input.get('value') if token_input else ""

    print(f"🔑 Token CSRF estratto: {token_val[:15]}..." if token_val else "⚠️ Token CSRF non trovato!")

    payload_login = {
        "Email": username,
        "Password": password,
        "__RequestVerificationToken": token_val,
        "RememberMe": "false"
    }
    
    headers_login = {
        'Referer': URL_LOGIN_PAGE,
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest'
    }

    print("🚀 3. Invio credenziali di login...")
    resp_login = session.post(URL_LOGIN_PAGE, data=payload_login, headers=headers_login, allow_redirects=True)
    print(f"📡 Status Code Login: {resp_login.status_code}")
    print("🍪 Cookie presenti dopo il login:", list(session.cookies.get_dict().keys()))

    # 3. Accesso alla formazione
    print("📋 4. Accesso alla pagina gestione formazione...")
    resp_form_page = session.get(URL_FORMAZIONE)
    
    if "Account/Login" in resp_form_page.url:
        print("❌ LOGIN FALLITO: Il server continua a reindirizzare al Login.")
        return

    print("✅ Autenticazione riuscita! Generazione payload di test...")
    soup_form = BeautifulSoup(resp_form_page.text, 'html.parser')
    
    token_form_input = soup_form.find('input', {'name': '__RequestVerificationToken'})
    token_form_val = token_form_input.get('value') if token_form_input else token_val

    base_params = {}
    for input_tag in soup_form.find_all('input', {'type': 'hidden'}):
        name = input_tag.get('name')
        if name:
            base_params[name] = input_tag.get('value', '')

    # Formazione di test (Sanchez titolare, Butez riserva)
    formazione_guida = [
        {"code": "6344", "role": "0", "stato": "T", "des": "SANCHEZ RO. (COMO)"}, 
        {"code": "7485", "role": "1", "stato": "T", "des": "MANGAS (MONZA)"},
        {"code": "5701", "role": "1", "stato": "T", "des": "OBERT (CAGLIARI)"},
        {"code": "5750", "role": "1", "stato": "T", "des": "OSTIGARD (GENOA)"},
        {"code": "2194", "role": "2", "stato": "T", "des": "CALHANOGLU (INTER)"},
        {"code": "2517", "role": "2", "stato": "T", "des": "DE BRUYNE (NAPOLI)"},
        {"code": "4220", "role": "2", "stato": "T", "des": "ZAMBO ANGUISSA (NAPOLI)"},
        {"code": "152",  "role": "2", "stato": "T", "des": "ZIELINSKI (INTER)"},
        {"code": "4923", "role": "3", "stato": "T", "des": "COLOMBO (GENOA)"},
        {"code": "5585", "role": "3", "stato": "T", "des": "MALEN (ROMA)"},
        {"code": "7523", "role": "3", "stato": "T", "des": "VARELA G. (MONZA)"},
        
        {"code": "6966", "role": "0", "stato": "1", "des": "BUTEZ (COMO)"},       
        {"code": "2809", "role": "0", "stato": "2", "des": "VIGORITO (COMO)"},     
        {"code": "2077", "role": "2", "stato": "3", "des": "PASALIC (ATALANTA)"},  
        {"code": "530",  "role": "2", "stato": "4", "des": "PELLEGRINI LO. (ROMA)"}, 
        {"code": "7070", "role": "2", "stato": "5", "des": "SUCIC P. (INTER)"},    
        {"code": "5791", "role": "2", "stato": "6", "des": "FRENDRUP (GENOA)"},    
        {"code": "6680", "role": "2", "stato": "A", "des": "KARLSTROM (UDINESE)"}, 
        {"code": "7409", "role": "2", "stato": "B", "des": "MEICHTRY (GENOA)"},    
        {"code": "7412", "role": "2", "stato": "C", "des": "MILLA (COMO)"},        
        {"code": "5994", "role": "1", "stato": "D", "des": "EBOSSE (UDINESE)"},    
        {"code": "5695", "role": "1", "stato": "E", "des": "HAPS (VENEZIA)"},      
        {"code": "2640", "role": "1", "stato": "F", "des": "KOLASINAC (ATALANTA)"}, 
        
        {"code": "2188", "role": "1", "stato": " ", "des": "MARUSIC (LAZIO)"},     
        {"code": "7351", "role": "3", "stato": " ", "des": "SANTOS A. (NAPOLI)"}   
    ]

    payload_data = {}
    league_code = base_params.get("[0].LeagueCode", "F1   ")
    tournament_code = base_params.get("[0].TournamentCode", "C34")
    coach_code = base_params.get("[0].CoachCode", "MB")
    team_code = base_params.get("[0].TeamCode", "MB34")

    for i, p in enumerate(formazione_guida):
        payload_data[f"[{i}].LeagueCode"] = league_code
        payload_data[f"[{i}].TournamentCode"] = tournament_code
        payload_data[f"[{i}].CoachCode"] = coach_code
        payload_data[f"[{i}].TeamCode"] = team_code
        payload_data[f"[{i}].PlayerRole"] = p["role"]
        payload_data[f"[{i}].PlayerCode"] = p["code"]
        
        date_key = f"[{i}].PlayerPlayDateTime"
        payload_data[date_key] = base_params.get(date_key, "20/09/2026 15:00:00")
        
        payload_data[f"[{i}].PlayerDes"] = p["des"]
        payload_data[f"[{i}].PlayerStatoFormaz"] = p["stato"]

    payload_data["[0].PlayerTipoSostituzioni"] = "N"
    if token_form_val:
        payload_data["__RequestVerificationToken"] = token_form_val

    headers_save = {
        'Referer': URL_FORMAZIONE,
        'Content-Type': 'application/x-www-form-urlencoded',
        'RequestVerificationToken': token_form_val
    }

    print("💾 5. Invio della richiesta SALVA a /Save...")
    resp_save = session.post(URL_SAVE, data=payload_data, headers=headers_save, allow_redirects=True)
    
    print(f"📡 Status Code Risposta: {resp_save.status_code}")
    print(f"🔗 URL finale: {resp_save.url}")

    if "Account/Login" in resp_save.url:
        print("❌ ERRORE: Reindirizzato al login durante il salvataggio.")
    else:
        print("✅ SALVATAGGIO RIUSCITO! Il server ha accettato e registrato i dati.")

if __name__ == "__main__":
    test_salva_formazione_fissa()
