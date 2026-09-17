import json
import re
import os
from datetime import datetime, timedelta

def formatta_cron(data_target, ora=12, minuto=0):
    """Genera la stringa cron: Minuto Ora Giorno Mese *"""
    return f"{minuto} {ora} {data_target.day} {data_target.month} *"

def aggiorna_file_workflow(cron_expr):
    """Aggiorna la riga del cron all'interno di .github/workflows/run_algorithm.yml"""
    path_yml = ".github/workflows/run_algorithm.yml"
    
    if not os.path.exists(path_yml):
        print(f"❌ File non trovato: {path_yml}")
        return

    with open(path_yml, 'r', encoding='utf-8') as f:
        contenuto = f.read()

    # Sostituisce la riga del cron (es. - cron: '0 12 21 8 *')
    nuovo_contenuto = re.sub(
        r"(-\s*cron:\s*['\"])[^'\"]+(['\"])",
        f"\\1{cron_expr}\\2",
        contenuto
    )

    with open(path_yml, 'w', encoding='utf-8') as f:
        f.write(nuovo_contenuto)
    
    print(f"✅ Workflow aggiornato con successo -> cron: '{cron_expr}'")

def calcola_prossima_schedulazione():
    if not os.path.exists('calendario.json'):
        print("❌ File calendario.json non trovato.")
        return

    with open('calendario.json', 'r', encoding='utf-8') as f:
        calendario = json.load(f)

    oggi = datetime.now()
    prossima_giornata = None
    data_giornata = None

    for g in calendario:
        dt_str = g.get('data_inizio')
        if dt_str:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
            # Consideriamo valida la giornata se la data di riferimento è oggi o futura
            if dt.date() >= oggi.date():
                prossima_giornata = g['giornata']
                data_giornata = dt
                break

    if not data_giornata:
        print("⚠️ Nessuna giornata futura trovata nel calendario.")
        return

    # Logica di calcolo giorni di anticipo:
    # 0 = Lunedì, 1 = Martedì, 2 = Mercoledì, 3 = Giovedì, 4 = Venerdì, 5 = Sabato, 6 = Domenica
    giorno_settimana = data_giornata.weekday()

    if giorno_settimana == 6:  # DOMENICA -> 2 giorni prima (VENERDÌ)
        giorni_anticipo = 2
    elif giorno_settimana == 2:  # MERCOLEDÌ -> 1 giorno prima (MARTEDÌ)
        giorni_anticipo = 1
    else:
        # Fallback di sicurezza per eventuali altre date: 1 giorno prima
        giorni_anticipo = 1

    data_esecuzione = data_giornata - timedelta(days=giorni_anticipo)
    cron_expr = formatta_cron(data_esecuzione, ora=12, minuto=0)

    print(f"📌 Prossima Giornata: G{prossima_giornata} ({data_giornata.strftime('%d/%m/%Y')})")
    print(f"⏰ Esecuzione schedulata per: {data_esecuzione.strftime('%A %d/%m/%Y')} alle 12:00 UTC")
    
    aggiorna_file_workflow(cron_expr)

if __name__ == "__main__":
    calcola_prossima_schedulazione()
