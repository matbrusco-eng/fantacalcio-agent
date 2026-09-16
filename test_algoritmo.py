import os
import requests
import io
import openpyxl
import json

URL_LOGIN = "https://www.fantacalcio.it/api/v1/User/login"
URL_EXCEL_STATS = "https://www.fantacalcio.it/api/v1/Excel/stats/21/5"

def calcola_score(fm, presenze, giornate_totali=20):
    c_pres = presenze / giornate_totali
    return round(fm * c_pres, 2)

def carica_rosa():
    with open('rosa.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def genera_formazione():
    username = os.environ.get("FANTACALCIO_USER")
    password = os.environ.get("FANTACALCIO_PASS")
    
    # 1. Caricamento della rosa da file JSON
    rosa = carica_rosa()
    # Creiamo un set con gli ID della mia rosa per lookup istantaneo O(1)
    ids_mia_rosa = {g['id']: g for g in rosa}
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.fantacalcio.it/'
    })
    
    # 2. Login
    res_login = session.post(URL_LOGIN, json={"username": username, "password": password})
    if res_login.status_code != 200 or not res_login.json().get("success"):
        print("❌ Errore Login")
        return

    # 3. Download Excel
    res_excel = session.get(URL_EXCEL_STATS)
    wb = openpyxl.load_workbook(io.BytesIO(res_excel.content), data_only=True)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    
    dati_rosa = []
    
    # 4. Matching basato su ID Giocatore (Indice 0 dell'Excel)
    for riga in rows[2:]:
        id_excel = riga[0]
        
        if id_excel in ids_mia_rosa:
            giocatore_info = ids_mia_rosa[id_excel]
            ruolo = riga[1]      # Ruolo Mantra (o riga[2] per Classico)
            presenze = riga[5] or 0
            fm = riga[7] or 0.0
            
            score = calcola_score(fm, presenze)
            dati_rosa.append({
                'id': id_excel,
                'nome': giocatore_info['nome'],
                'ruolo': ruolo,
                'fm': fm,
                'presenze': presenze,
                'score': score
            })

    # Ordina per Score decrescente
    dati_rosa.sort(key=lambda x: x['score'], reverse=True)

    # 5. Selezione Formazione
    titolari = []
    
    # Minimo 1 Portiere
    portieri = [g for g in dati_rosa if g['ruolo'] == 'P']
    if portieri:
        titolari.append(portieri[0])
    
    # Minimo 3 Difensori
    difensori = [g for g in dati_rosa if g['ruolo'] == 'D']
    titolari.extend(difensori[:3])
    
    # Restanti 7 giocatori di movimento a più alto score
    ids_scelti = {g['id'] for g in titolari}
    movimento_restante = [g for g in dati_rosa if g['ruolo'] != 'P' and g['id'] not in ids_scelti]
    titolari.extend(movimento_restante[:7])

    # Panchina
    ids_titolari = {g['id'] for g in titolari}
    panchina = [g for g in dati_rosa if g['id'] not in ids_titolari]

    # Stampa Output
    print("\n--- ⚽ TITOLARI CONSIGLIATI ---")
    for g in titolari:
        print(f"[{g['ruolo']}] (ID: {g['id']}) {g['nome']} - Score: {g['score']} (FM: {g['fm']}, Pres: {g['presenze']})")
        
    print("\n--- 🪑 PANCHINA ---")
    for g in panchina:
        print(f"[{g['ruolo']}] (ID: {g['id']}) {g['nome']} - Score: {g['score']} (FM: {g['fm']}, Pres: {g['presenze']})")

if __name__ == "__main__":
    genera_formazione()
