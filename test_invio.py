import os
import requests
from bs4 import BeautifulSoup

URL_HOME = "https://www.fanta-gazzetta.it/"
URL_LOGIN_PAGE = "https://www.fanta-gazzetta.it/Account/Login"
URL_FORMAZIONE = "https://www.fanta-gazzetta.it/api/CoachCurrentTeams/InvioFormazione"
URL_SAVE = "https://www.fanta-gazzetta.it/api/CoachCurrentTeams/Save"

def test_salva_formazione_fissa():
    username = os.environ.get("FANTA_USER", "").strip()
    password = os.environ.get("FANTA_PASS", "").strip()
    
    if not username or not password:
        print("❌ Errore: FANTA_USER o FANTA_PASS non impostati nei Secrets.")
        return

    print(f"📏 Verifica Password: L'ultimo carattere letto è '{password[-1]}'")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
    })

    # 1. Inizializzazione sessione sulla Home
    print("🌐 1. Inizializzazione sessione Home...")
    session.get(URL_HOME)

    # 2. Login Page
    print("🔑 2. Recupero Token Login...")
    resp_login_page = session.get(URL_LOGIN_PAGE)
    soup = BeautifulSoup(resp_login_page.text, 'html.parser')
    
    token_input = soup.find('input', {'name': '__RequestVerificationToken'})
    token_val = token_input.get('value') if token_input else ""

    payload_login = {
        "Email": username,
        "Password": password,
        "__RequestVerificationToken": token_val,
        "RememberMe": "false"
    }

    headers_login = {
        'Referer': URL_LOGIN_PAGE,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.fanta-gazzetta.it'
    }

    print("🚀 3. Invio credenziali...")
    resp_login = session.post(URL_LOGIN_PAGE, data=payload_login, headers=headers_login, allow_redirects=True)
    
    cookies = list(session.cookies.get_dict().keys())
    print("🍪 Cookie ottenuti post-login:", cookies)

    if not any(".AspNetCore.Cookies" in c or ".AspNetCore.Identity" in c for c in cookies):
        soup_resp = BeautifulSoup(resp_login.text, 'html.parser')
        err_msg = soup_resp.find(class_=["text-danger", "validation-summary-errors"])
        print(f"❌ Login ancora rifiutato. Errore: {err_msg.get_text(strip=True) if err_msg else 'Non specificato'}")
        return

    print("🎉 LOGIN RIUSCITO CON SUCCESSO!")

    # 3. Accesso alla formazione
    print("📋 4. Recupero dati formazione...")
    resp_form_page = session.get(URL_FORMAZIONE)
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

    print("💾 5. Invio richiesta SALVA a /Save...")
    resp_save = session.post(URL_SAVE, data=payload_data, headers=headers_save, allow_redirects=True)
    
    print(f"📡 Status Code Risposta: {resp_save.status_code}")
    print(f"🔗 URL finale: {resp_save.url}")

    if "Account/Login" in resp_save.url:
        print("❌ ERRORE: Reindirizzato al login durante il salvataggio.")
    else:
        print("✅ SALVATAGGIO RIUSCITO! Vai a verificare sul sito se il portiere è cambiato!")

if __name__ == "__main__":
    test_salva_formazione_fissa()
