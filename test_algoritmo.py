import os
import requests
import io
import openpyxl
import json
import smtplib
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

URL_LOGIN = "https://www.fantacalcio.it/api/v1/User/login"
URL_EXCEL_STATS = "https://www.fantacalcio.it/api/v1/Excel/stats/21/5"
URL_PROBABILI_FORMAZIONI = "https://www.fantacalcio.it/probabili-formazioni-serie-a"

RUOLI_ORDINE = {'P': 1, 'D': 2, 'C': 3, 'A': 4}

def calcola_score(fm, presenze, giornate_totali):
    if giornate_totali == 0:
        return 0.0
    c_pres = presenze / giornate_totali
    return round(fm * c_pres, 2)

def carica_rosa():
    with open('rosa.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def recupera_stato_infermeria_live(session):
    """
    Effettua lo scraping della pagina Probabili Formazioni di Fantacalcio.it
    per estrarre Stato (Titolare/Panchina/Infortunato/Squalificato), % Voto e Note Infortuni.
    """
    dati_probabili = {}
    try:
        res = session.get(URL_PROBABILI_FORMAZIONI)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Cerca i blocchi dei giocatori nelle schede partita
            for player_card in soup.find_all('div', class_=lambda c: c and 'player-item' in c):
                nome_el = player_card.find('span', class_='name')
                perc_el = player_card.find('span', class_='percentage')
                note_el = player_card.find('span', class_='status-text') or player_card.find('div', class_='info')

                if nome_el:
                    nome = nome_el.text.strip().upper()
                    perc = perc_el.text.strip() if perc_el else "50%"
                    
                    # Riconoscimento stato
                    card_class = player_card.get('class', [])
                    if 'starter' in card_class or 'titolare' in card_class:
                        stato = "TITOLARE"
                    elif 'bench' in card_class or 'panchina' in card_class:
                        stato = "PANCHINA"
                    elif 'injured' in card_class or 'infortunato' in card_class:
                        stato = "INFORTUNATO"
                    elif 'suspended' in card_class or 'squalificato' in card_class:
                        stato = "SQUALIFICATO"
                    else:
                        stato = "TITOLARE" if int(perc.replace('%','')) >= 60 else "PANCHINA"

                    note = note_el.text.strip() if note_el else ("Disponibile" if stato in ["TITOLARE", "PANCHINA"] else stato)
                    
                    dati_probabili[nome] = {
                        'stato': stato,
                        'perc_voto': perc,
                        'note': note
                    }
    except Exception as e:
        print(f"⚠️ Errore durante lo scraping delle probabili formazioni: {e}")
    
    return dati_probabili

def invia_email_report(titolari, panchina, dati_rosa, giornate_totali):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")
    email_to = os.environ.get("EMAIL_TO", gmail_user)

    if not gmail_user or not gmail_pass:
        print("⚠️ Secret GMAIL_USER o GMAIL_APP_PASSWORD non trovati. Email non inviata.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"⚽ Fantacalcio - Formazione Consigliata e Stato Rosa (G{giornate_totali})"
    msg["From"] = gmail_user
    msg["To"] = email_to

    # 1. Tabella Titolari (P -> D -> C -> A con Gol e Assist)
    titolari_ordinati = sorted(titolari, key=lambda x: (RUOLI_ORDINE.get(x['ruolo'], 99), -x['score']))
    html_titolari = ""
    for g in titolari_ordinati:
        html_titolari += f"""
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 3px 6px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 6px;"><b>{g['nome']}</b></td>
            <td style="padding: 3px 6px; text-align: center; color: #2e7d32; font-weight: bold;">{g['score']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['fm']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['gol']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['assist']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['presenze']}/{giornate_totali}</td>
        </tr>
        """

    # 2. Tabella Panchina (Mantenuta per Numerazione con Gol e Assist)
    html_panchina = ""
    for i, g in enumerate(panchina, 1):
        html_panchina += f"""
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 3px 6px; text-align: center;">{i}</td>
            <td style="padding: 3px 6px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 6px;">{g['nome']}</td>
            <td style="padding: 3px 6px; text-align: center; font-weight: bold;">{g['score']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['fm']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['gol']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['assist']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['presenze']}/{giornate_totali}</td>
        </tr>
        """

    # 3. Tabella Stato Completo Rosa (P -> D -> C -> A con Stato, % Voto e Note reali)
    rosa_ordinata_stato = sorted(dati_rosa, key=lambda x: (RUOLI_ORDINE.get(x['ruolo'], 99), -x['score']))
    html_stato_rosa = ""
    for g in rosa_ordinata_stato:
        colore_stato = "#2e7d32" if g['stato'] == "TITOLARE" else ("#e65100" if g['stato'] == "PANCHINA" else "#c62828")
        html_stato_rosa += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 3px 6px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 6px;"><b>{g['nome']}</b></td>
            <td style="padding: 3px 6px; text-align: center; color: {colore_stato}; font-weight: bold;">{g['stato']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['perc_voto']}</td>
            <td style="padding: 3px 6px; font-size: 11px;">{g['note']}</td>
        </tr>
        """

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.2; font-size: 13px;">
        <h3 style="color: #1a237e; margin: 0 0 8px 0;">⚽ Report Formazione Fantacalcio - Giornata {giornate_totali}</h3>
        
        <b style="color: #2e7d32; font-size: 14px;">🔥 TITOLARI CONSIGLIATI</b>
        <table style="width: 100%; max-width: 580px; border-collapse: collapse; background: #f9f9f9; margin: 4px 0 12px 0;">
            <thead>
                <tr style="background-color: #2e7d32; color: white;">
                    <th style="padding: 4px 6px;">R</th>
                    <th style="padding: 4px 6px; text-align: left;">Nome</th>
                    <th style="padding: 4px 6px;">Score</th>
                    <th style="padding: 4px 6px;">FM</th>
                    <th style="padding: 4px 6px;">G</th>
                    <th style="padding: 4px 6px;">A</th>
                    <th style="padding: 4px 6px;">Pres.</th>
                </tr>
            </thead>
            <tbody>
                {html_titolari}
            </tbody>
        </table>

        <b style="color: #e65100; font-size: 14px;">🪑 PANCHINA PER NUMERAZIONE (P -> A -> C -> D)</b>
        <table style="width: 100%; max-width: 580px; border-collapse: collapse; background: #f9f9f9; margin: 4px 0 16px 0;">
            <thead>
                <tr style="background-color: #e65100; color: white;">
                    <th style="padding: 4px 6px;">#</th>
                    <th style="padding: 4px 6px;">R</th>
                    <th style="padding: 4px 6px; text-align: left;">Nome</th>
                    <th style="padding: 4px 6px;">Score</th>
                    <th style="padding: 4px 6px;">FM</th>
                    <th style="padding: 4px 6px;">G</th>
                    <th style="padding: 4px 6px;">A</th>
                    <th style="padding: 4px 6px;">Pres.</th>
                </tr>
            </thead>
            <tbody>
                {html_panchina}
            </tbody>
        </table>

        <hr style="border: 0; border-top: 1px solid #ccc; margin: 12px 0;">

        <b style="color: #37474f; font-size: 14px;">📊 STATO E DISPONIBILITÀ ROSA (PARSING INFERMERIA LIVE)</b>
        <table style="width: 100%; max-width: 580px; border-collapse: collapse; font-size: 12px; margin-top: 4px;">
            <thead>
                <tr style="background-color: #37474f; color: white;">
                    <th style="padding: 4px 6px;">R</th>
                    <th style="padding: 4px 6px; text-align: left;">Nome</th>
                    <th style="padding: 4px 6px;">Stato</th>
                    <th style="padding: 4px 6px;">% Voto</th>
                    <th style="padding: 4px 6px; text-align: left;">Note / Infortuni</th>
                </tr>
            </thead>
            <tbody>
                {html_stato_rosa}
            </tbody>
        </table>
        <p style="font-size: 11px; color: #777; margin-top: 10px;"><i>Report generato automaticamente dall'algoritmo del Mostro v10.0.</i></p>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, email_to, msg.as_string())
        server.quit()
        print("📧 Email con il report compatto inviata con successo!")
    except Exception as e:
        print(f"❌ Errore durante l'invio dell'email: {e}")

def genera_formazione():
    username = os.environ.get("FANTACALCIO_USER")
    password = os.environ.get("FANTACALCIO_PASS")
    
    rosa = carica_rosa()
    ids_mia_rosa = {g['id']: g for g in rosa}
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.fantacalcio.it/'
    })
    
    res_login = session.post(URL_LOGIN, json={"username": username, "password": password})
    if res_login.status_code != 200 or not res_login.json().get("success"):
        print("❌ Errore Login")
        return

    # Download Excel Statistiche
    res_excel = session.get(URL_EXCEL_STATS)
    wb = openpyxl.load_workbook(io.BytesIO(res_excel.content), data_only=True)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    
    # Scraping stato infermeria e probabili formazioni
    dati_probabili = recupera_stato_infermeria_live(session)
    
    presenze_totali = [riga[5] for riga in rows[2:] if isinstance(riga[5], (int, float))]
    giornate_totali = max(presenze_totali) if presenze_totali else 1
    
    dati_rosa = []
    
    for riga in rows[2:]:
        id_excel = riga[0]
        if id_excel in ids_mia_rosa:
            giocatore_info = ids_mia_rosa[id_excel]
            ruolo = riga[1]
            presenze = riga[5] or 0
            fm = riga[7] or 0.0
            gol = riga[8] or 0
            assist = riga[9] or 0
            
            score = calcola_score(fm, presenze, giornate_totali)
            
            # Recupera dati reali da probabili formazioni / infermeria
            nome_upper = giocatore_info['nome'].upper()
            info_live = dati_probabili.get(nome_upper, {})
            
            stato = info_live.get('stato', "TITOLARE" if presenze > 0 else "PANCHINA")
            perc_voto = info_live.get('perc_voto', f"{min(100, int((presenze/giornate_totali)*100))}%")
            note = info_live.get('note', "Disponibile")

            dati_rosa.append({
                'id': id_excel,
                'nome': giocatore_info['nome'],
                'ruolo': ruolo,
                'fm': fm,
                'gol': gol,
                'assist': assist,
                'presenze': presenze,
                'score': score,
                'stato': stato,
                'perc_voto': perc_voto,
                'note': note
            })

    dati_rosa.sort(key=lambda x: x['score'], reverse=True)

    # 1. Titolari
    titolari = []
    portieri = [g for g in dati_rosa if g['ruolo'] == 'P']
    if portieri:
        titolari.append(portieri[0])
    
    difensori = [g for g in dati_rosa if g['ruolo'] == 'D']
    titolari.extend(difensori[:3])
    
    ids_scelti = {g['id'] for g in titolari}
    movimento_restante = [g for g in dati_rosa if g['ruolo'] != 'P' and g['id'] not in ids_scelti]
    titolari.extend(movimento_restante[:7])

    # 2. Panchina per Numerazione (P -> A -> C -> D)
    ids_titolari = {g['id'] for g in titolari}
    panchina_grezza = [g for g in dati_rosa if g['id'] not in ids_titolari]
    
    p_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'P'], key=lambda x: x['score'], reverse=True)
    a_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'A'], key=lambda x: x['score'], reverse=True)
    c_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'C'], key=lambda x: x['score'], reverse=True)
    d_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'D'], key=lambda x: x['score'], reverse=True)
    
    panchina = p_panchina + a_panchina + c_panchina + d_panchina

    # Invio Email
    invia_email_report(titolari, panchina, dati_rosa, giornate_totali)

    return titolari, panchina

if __name__ == "__main__":
    genera_formazione()
