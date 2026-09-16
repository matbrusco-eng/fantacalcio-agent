import os
import requests
import io
import openpyxl
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

URL_LOGIN = "https://www.fantacalcio.it/api/v1/User/login"
URL_EXCEL_STATS = "https://www.fantacalcio.it/api/v1/Excel/stats/21/5"

# Mappatura per l'ordinamento rigoroso dei ruoli: P -> D -> C -> A
RUOLI_ORDINE = {'P': 1, 'D': 2, 'C': 3, 'A': 4}

def calcola_score(fm, presenze, giornate_totali):
    if giornate_totali == 0:
        return 0.0
    c_pres = presenze / giornate_totali
    return round(fm * c_pres, 2)

def carica_rosa():
    with open('rosa.json', 'r', encoding='utf-8') as f:
        return json.load(f)

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

    # 1. Tabella Titolari (Ordinati P -> D -> C -> A)
    titolari_ordinati = sorted(titolari, key=lambda x: (RUOLI_ORDINE.get(x['ruolo'], 99), -x['score']))
    html_titolari = ""
    for g in titolari_ordinati:
        html_titolari += f"""
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 3px 8px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 8px;"><b>{g['nome']}</b></td>
            <td style="padding: 3px 8px; text-align: center; color: #2e7d32; font-weight: bold;">{g['score']}</td>
            <td style="padding: 3px 8px; text-align: center;">{g['fm']}</td>
            <td style="padding: 3px 8px; text-align: center;">{g['presenze']}/{giornate_totali}</td>
        </tr>
        """

    # 2. Tabella Panchina (Mantenuta per Numerazione)
    html_panchina = ""
    for i, g in enumerate(panchina, 1):
        html_panchina += f"""
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 3px 8px; text-align: center;">{i}</td>
            <td style="padding: 3px 8px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 8px;">{g['nome']}</td>
            <td style="padding: 3px 8px; text-align: center; font-weight: bold;">{g['score']}</td>
            <td style="padding: 3px 8px; text-align: center;">{g['fm']}</td>
            <td style="padding: 3px 8px; text-align: center;">{g['presenze']}/{giornate_totali}</td>
        </tr>
        """

    # 3. Tabella Stato Completo della Rosa (Stile agent.py: P -> D -> C -> A con Stato/Infortuni/%)
    rosa_ordinata_stato = sorted(dati_rosa, key=lambda x: (RUOLI_ORDINE.get(x['ruolo'], 99), -x['score']))
    html_stato_rosa = ""
    for g in rosa_ordinata_stato:
        # Colore di evidenziazione per stato
        colore_stato = "#2e7d32" if g['stato'] == "Titolare" else ("#e65100" if g['stato'] == "Panchina" else "#c62828")
        html_stato_rosa += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 3px 8px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 8px;">{g['nome']}</td>
            <td style="padding: 3px 8px; text-align: center; color: {colore_stato}; font-weight: bold;">{g['stato']}</td>
            <td style="padding: 3px 8px; text-align: center;">{g['perc_voto']}</td>
            <td style="padding: 3px 8px;">{g['note']}</td>
        </tr>
        """

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.2; font-size: 13px;">
        <h3 style="color: #1a237e; margin: 0 0 8px 0;">⚽ Report Formazione Fantacalcio - Giornata {giornate_totali}</h3>
        
        <b style="color: #2e7d32; font-size: 14px;">🔥 TITOLARI CONSIGLIATI</b>
        <table style="width: 100%; max-width: 550px; border-collapse: collapse; background: #f9f9f9; margin: 4px 0 12px 0;">
            <thead>
                <tr style="background-color: #2e7d32; color: white;">
                    <th style="padding: 4px 8px;">R</th>
                    <th style="padding: 4px 8px; text-align: left;">Nome</th>
                    <th style="padding: 4px 8px;">Score</th>
                    <th style="padding: 4px 8px;">FM</th>
                    <th style="padding: 4px 8px;">Pres.</th>
                </tr>
            </thead>
            <tbody>
                {html_titolari}
            </tbody>
        </table>

        <b style="color: #e65100; font-size: 14px;">🪑 PANCHINA PER NUMERAZIONE (P -> A -> C -> D)</b>
        <table style="width: 100%; max-width: 550px; border-collapse: collapse; background: #f9f9f9; margin: 4px 0 16px 0;">
            <thead>
                <tr style="background-color: #e65100; color: white;">
                    <th style="padding: 4px 8px;">#</th>
                    <th style="padding: 4px 8px;">R</th>
                    <th style="padding: 4px 8px; text-align: left;">Nome</th>
                    <th style="padding: 4px 8px;">Score</th>
                    <th style="padding: 4px 8px;">FM</th>
                    <th style="padding: 4px 8px;">Pres.</th>
                </tr>
            </thead>
            <tbody>
                {html_panchina}
            </tbody>
        </table>

        <hr style="border: 0; border-top: 1px solid #ccc; margin: 12px 0;">

        <b style="color: #37474f; font-size: 14px;">📊 STATO E DISPONIBILITÀ ROSA</b>
        <table style="width: 100%; max-width: 550px; border-collapse: collapse; font-size: 12px; margin-top: 4px;">
            <thead>
                <tr style="background-color: #37474f; color: white;">
                    <th style="padding: 4px 8px;">R</th>
                    <th style="padding: 4px 8px; text-align: left;">Nome</th>
                    <th style="padding: 4px 8px;">Stato</th>
                    <th style="padding: 4px 8px;">% Voto</th>
                    <th style="padding: 4px 8px; text-align: left;">Note / Infortuni</th>
                </tr>
            </thead>
            <tbody>
                {html_stato_rosa}
            </tbody>
        </table>
        <p style="font-size: 11px; color: #777; margin-top: 10px;"><i>Report generato automaticamente dall'algoritmo del Mostro.</i></p>
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.fantacalcio.it/'
    })
    
    res_login = session.post(URL_LOGIN, json={"username": username, "password": password})
    if res_login.status_code != 200 or not res_login.json().get("success"):
        print("❌ Errore Login")
        return

    res_excel = session.get(URL_EXCEL_STATS)
    wb = openpyxl.load_workbook(io.BytesIO(res_excel.content), data_only=True)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    
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
            
            score = calcola_score(fm, presenze, giornate_totali)
            
            # Simulazione campi di titolarità/stato da agent.py (in attesa di scraping/API diretta)
            stato = "Titolare" if presenze > 0 else "Indisponibile"
            perc_voto = f"{min(100, int((presenze/giornate_totali)*100))}%" if giornate_totali > 0 else "0%"
            note = "Disponibile" if presenze > 0 else "Infortunato / Squalificato"

            dati_rosa.append({
                'id': id_excel,
                'nome': giocatore_info['nome'],
                'ruolo': ruolo,
                'fm': fm,
                'presenze': presenze,
                'score': score,
                'stato': stato,
                'perc_voto': perc_voto,
                'note': note
            })

    dati_rosa.sort(key=lambda x: x['score'], reverse=True)

    # 1. Selezione Titolari
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

    # Invio Email con le nuove formattazioni
    invia_email_report(titolari, panchina, dati_rosa, giornate_totali)

    return titolari, panchina

if __name__ == "__main__":
    genera_formazione()
