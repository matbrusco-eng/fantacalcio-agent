import os
import requests
from bs4 import BeautifulSoup

URL_LOGIN = "https://www.fanta-gazzetta.it/Account/Login"
URL_FORMAZIONE = "https://www.fanta-gazzetta.it/api/CoachCurrentTeams/InvioFormazione"
URL_SEND = "https://www.fanta-gazzetta.it/api/CoachCurrentTeams/Send"

def test_invio_formazione():
    username = os.environ.get("FANTA_USER")
    password = os.environ.get("FANTA_PASS")
    
    if not username or not password:
        print("❌ Errore: FANTA_USER o FANTA_PASS non impostati nei Secrets di GitHub.")
        return

    # Usiamo una sessione per mantenere i cookie di autenticazione
    session = requests.Session()
    
    # 1. Carichiamo la pagina di login per prendere il token CSRF di ASP.NET
    print("🌐 Connessione alla pagina di login...")
    resp_login_page = session.get(URL_LOGIN)
    if resp_login_page.status_code != 200:
        print(f"❌ Impossibile raggiungere il login. Status: {resp_login_page.status_code}")
        return

    soup = BeautifulSoup(resp_login_page.text, 'html.parser')
    token_input = soup.find('input', {'name': '__RequestVerificationToken'})
    token_val = token_input.get('value') if token_input else ""

    # 2. Eseguiamo il POST di Login
    payload_login = {
        "Email": username,
        "Password": password,
        "__RequestVerificationToken": token_val
    }
    
    print("🔑 Effettuando il login...")
    resp_login = session.post(URL_LOGIN, data=payload_login, allow_redirects=True)
    
    # Verifichiamo se il login è andato a buon fine (di solito reindirizza alla home o a un'area protetta)
    print(f"📡 Status Code Login: {resp_login.status_code}")

    # 3. Visitiamo la pagina di invio formazione per raccogliere gli input e i dati attuali presenti sul server
    print("📋 Apertura della pagina formazione per raccogliere i dati attuali...")
    resp_form_page = session.get(URL_FORMAZIONE)
    if resp_form_page.status_code != 200:
        print(f"❌ Impossibile accedere alla pagina di gestione formazione. Status: {resp_form_page.status_code}")
        return

    soup_form = BeautifulSoup(resp_form_page.text, 'html.parser')
    
    # Raccogliamo tutti i campi input nascosti e le selezioni presenti nel form di invio
    form_data = {}
    
    # Prendiamo tutti gli input (hidden, select, ecc.) presenti nella pagina
    for input_tag in soup_form.find_all(['input', 'select']):
        name = input_tag.get('name')
        if not name:
            continue
            
        # Se è una select, prendiamo l'opzione selezionata
        if input_tag.name == 'select':
            selected_option = input_tag.find('option', selected=True) or input_tag.find('option')
            value = selected_option.get('value') if selected_option else ""
            form_data[name] = value
        else:
            # Per gli input normali o hidden
            # Gestiamo i checkbox se necessario, ma qui abbiamo principalmente hidden e select
            if input_tag.get('type') == 'checkbox' and not input_tag.has_attr('checked'):
                continue
            form_data[name] = input_tag.get('value', '')

    print(f"📦 Raccolti {len(form_data)} parametri dal form di formazione.")

    # 4. Eseguiamo il POST di invio formazione (simulando esattamente il tasto Invia)
    print("🚀 Invio della formazione in corso...")
    resp_send = session.post(URL_SEND, data=form_data, allow_redirects=True)
    
    print(f"📡 Status Code Invio: {resp_send.status_code}")
    print(f"🔗 URL finale: {resp_send.url}")

    # Verifichiamo dall'HTML di risposta se compare la scritta di successo che hai visto prima
    if "Formazione inviata" in resp_send.text or resp_send.status_code == 200:
        print("✅ TEST SUPERATO: Il server ha accettato l'invio della formazione!")
    else:
        print("⚠️ L'invio ha risposto ma la conferma non è esplicita. Controlla il sito.")

if __name__ == "__main__":
    test_invio_formazione()
