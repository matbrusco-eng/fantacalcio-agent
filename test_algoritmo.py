import os
import requests
import io
import openpyxl
import json

URL_LOGIN = "https://www.fantacalcio.it/api/v1/User/login"
URL_EXCEL_STATS = "https://www.fantacalcio.it/api/v1/Excel/stats/21/5"

def calcola_score(fm, presenze, giornate_totali):
    if giornate_totali == 0:
        return 0.0
    c_pres = presenze / giornate_totali
    return round(fm * c_pres, 2)

def carica_rosa():
    with open('rosa.json', 'r', encoding='utf-8') as f:
        return json.load(f)

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
    
    # 1. Determinazione dinamica delle giornate giocate (max presenze nell'intero file)
    presenze_totali = [riga[5] for riga in rows[2:] if isinstance(riga[5], (int, float))]
    giornate_totali = max(presenze_totali) if presenze_totali else 1
    print(f"ℹ️ Giornate di campionato rilevate: {giornate_totali}")
    
    dati_rosa = []
    
    # 2. Matching su ID ed estrazione dati
    for riga in rows[2:]:
        id_excel = riga[0]
        if id_excel in ids_mia_rosa:
            giocatore_info = ids_mia_rosa[id_excel]
            ruolo = riga[1]      # Ruolo Mantra / Classico
            presenze = riga[5] or 0
            fm = riga[7] or 0.0
            
            score = calcola_score(fm, presenze, giornate_totali)
            dati_rosa.append({
                'id': id_excel,
                'nome': giocatore_info['nome'],
                'ruolo': ruolo,
                'fm': fm,
                'presenze': presenze,
                'score': score
            })

    # Ordina la rosa per Score decrescente
    dati_rosa.sort(key=lambda x: x['score'], reverse=True)

    # 3. Selezione Titolari
    titolari = []
    
    # Requisito 1: Miglior Portiere
    portieri = [g for g in dati_rosa if g['ruolo'] == 'P']
    if portieri:
        titolari.append(portieri[0])
    
    # Requisito 2: Minimo 3 Difensori
    difensori = [g for g in dati_rosa if g['ruolo'] == 'D']
    titolari.extend(difensori[:3])
    
    # Requisito 3: I migliori 7 di movimento liberi
    ids_scelti = {g['id'] for g in titolari}
    movimento_restante = [g for g in dati_rosa if g['ruolo'] != 'P' and g['id'] not in ids_scelti]
    titolari.extend(movimento_restante[:7])

    # 4. Ordinamento Panchina per Numerazione (P -> A -> C -> D per Score decrescente)
    ids_titolari = {g['id'] for g in titolari}
    panchina_grezza = [g for g in dati_rosa if g['id'] not in ids_titolari]
    
    p_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'P'], key=lambda x: x['score'], reverse=True)
    a_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'A'], key=lambda x: x['score'], reverse=True)
    c_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'C'], key=lambda x: x['score'], reverse=True)
    d_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'D'], key=lambda x: x['score'], reverse=True)
    
    panchina = p_panchina + a_panchina + c_panchina + d_panchina

    # Output Grafico
    print("\n--- ⚽ TITOLARI CONSIGLIATI ---")
    for g in titolari:
        print(f"[{g['ruolo']}] (ID: {g['id']}) {g['nome']} - Score: {g['score']} (FM: {g['fm']}, Pres: {g['presenze']}/{giornate_totali})")
        
    print("\n--- 🪑 PANCHINA PER NUMERAZIONE (P -> A -> C -> D) ---")
    for i, g in enumerate(panchina, 1):
        print(f"{i}. [{g['ruolo']}] (ID: {g['id']}) {g['nome']} - Score: {g['score']} (FM: {g['fm']}, Pres: {g['presenze']}/{giornate_totali})")

    return titolari, panchina

if __name__ == "__main__":
    genera_formazione()
