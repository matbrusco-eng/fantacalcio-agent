import os
import requests
from bs4 import BeautifulSoup

URL_HOME = "https://www.fanta-gazzetta.it/"
URL_LOGIN_PAGE = "https://www.fanta-gazzetta.it/Account/Login"
URL_FORMAZIONE = "https://www.fanta-gazzetta.it/api/CoachCurrentTeams/InvioFormazione"

def test_invio_definitivo():
    username = os.environ.get("FANTA_USER", "").strip()
    password = os.environ.get("FANTA_PASS", "").strip()
    
    if not username or not password:
        print("❌ Errore: FANTA_USER o FANTA_PASS non impostati nei Secrets.")
        return

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
    })

    # 1. Inizializzazione sessione Home
    print("🌐 1. Inizializzazione sessione...")
    session.get(URL_HOME)

    # 2. Login Page & Token CSRF
    print("🔑 2. Login in corso...")
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

    resp_login = session.post(URL_LOGIN_PAGE, data=payload_login, headers=headers_login, allow_redirects=True)
    cookies = list(session.cookies.get_dict().keys())
    
    if not any(".AspNetCore.Identity" in c or ".AspNetCore.Cookies" in c for c in cookies):
        print("❌ Errore: Cookie di autenticazione non presente.")
        return

    print("🎉 LOGIN EFFETTUATO CON SUCCESSO!")

    # 3. Lettura dati di formazione per allineare i codici
    print("📋 3. Accesso alla pagina formazione...")
    resp_form_page = session.get(URL_FORMAZIONE)
    
    if "Account/Login" in resp_form_page.url:
        print("❌ Errore: Sessione persa dopo il reindirizzamento alla formazione.")
        return

    soup_form = BeautifulSoup(resp_form_page.text, 'html.parser')
    
    token_form_input = soup_form.find('input', {'name': '__RequestVerificationToken'})
    token_form_val = token_form_input.get('value') if token_form_input else token_val

    base_params = {}
    for input_tag in soup_form.find_all('input', {'type': 'hidden'}):
        name = input_tag.get('name')
        if name:
            base_params[name] = input_tag.get('value', '')

    # Formazione di test (Invertiamo: Butez titolare, Sanchez in panchina)
    formazione_guida = [
        # Titolari (0-10)
        {"code": "6966", "role": "0", "stato": "T", "des": "BUTEZ (COMO)"}, 
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
        
        # Panchina (11-22)
        {"code": "6344", "role": "0", "stato": "1", "des": "SANCHEZ RO. (COMO)"},       
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
        
        # Tribuna (23-24)
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
    payload_data["submitButton"] = "Invia"
    if token_form_val:
        payload_data["__RequestVerificationToken"] = token_form_val

    headers_save = {
        'Referer': URL_FORMAZIONE,
        'Content-Type': 'application/x-www-form-urlencoded',
        'RequestVerificationToken': token_form_val
    }

    # 4. Scrittura formazione (Invio Definitivo)
    print("🚀 4. Invio DEFINITIVO della formazione a /InvioFormazione...")
    resp_save = session.post(URL_FORMAZIONE, data=payload_data, headers=headers_save, allow_redirects=True)
    
    print(f"📡 Status Code Risposta: {resp_save.status_code}")
    print(f"🔗 URL finale post-invio: {resp_save.url}")

    if "Account/Login" in resp_save.url:
        print("❌ Invio fallito: reindirizzato al login.")
    else:
        print("✅ INVIO DEFINITIVO COMPLETATO! Aggiorna la pagina sul browser: dovresti vedere il banner verde con Butez titolare!")

if __name__ == "__main__":
    test_invio_definitivo()
