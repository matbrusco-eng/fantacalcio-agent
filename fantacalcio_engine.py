import json
import pandas as pd
import os

def load_data():
    # Legge dinamicamente la rosa attuale (aggiornata da te)
    with open('rosa.json', 'r', encoding='utf-8') as f:
        rosa = json.load(f)
        
    # Legge lo storico delle giornate
    if os.path.exists('storico_giornate.json'):
        with open('storico_giornate.json', 'r', encoding='utf-8') as f:
            storico = json.load(f)
    else:
        storico = {}
        
    stats_file = 'Statistiche_Fantacalcio_Stagione_2026_27_Italia (3).xlsx'
    df_stats = pd.read_excel(stats_file, sheet_name='Tutti', header=1)
    df_stats['Id_clean'] = df_stats['Id'].astype(str).str.strip().str.lstrip('0')
    
    return rosa, storico, df_stats

def calculate_player_metrics(rosa, storico, df_stats):
    evaluations = []
    
    for p in rosa:
        pid = str(p['id'])
        nome = p['nome']
        ruolo = p['ruolo']
        
        # Match con le statistiche ufficiali
        match_stats = df_stats[df_stats['Id_clean'] == pid]
        if not match_stats.empty:
            row = match_stats.iloc[0]
            pv = float(row.get('Pv', 0))
            fm_tot = float(row.get('Fm', 0))
            mv_tot = float(row.get('Mv', 0))
            gf = float(row.get('Gf', 0))
            ass = float(row.get('Ass', 0))
            squadra = str(row.get('Squadra', 'N/D'))
        else:
            pv = 0
            fm_tot = 0.0
            mv_tot = 0.0
            gf = 0.0
            ass = 0.0
            squadra = 'N/D'
            
        # Gestione dinamica dello storico: se il giocatore è nuovo nella rosa 
        # e non ha ancora uno storico registrato, usiamo la FantaMedia stagionale come base
        if pid in storico and len(storico[pid].get('voti_settimanali', [])) > 0:
            voti = storico[pid]['voti_settimanali']
            ultime_3 = voti[-3:]
            fm_recent = sum(ultime_3) / len(ultime_3)
        else:
            fm_recent = fm_tot
            
        # Delta Forma & Trend
        delta_forma = round(fm_recent - fm_tot, 2)
        if pv == 0:
            trend = "⚪ N.D."
        elif delta_forma >= 0.3:
            trend = "📈 In Crescita"
        elif delta_forma <= -0.3:
            trend = "📉 In Calo"
        else:
            trend = "➡️ Stabile"
            
        # Score potenziale ponderato (60% totale, 40% recente + bonus)
        score_potenziale = round((fm_tot * 0.6) + (fm_recent * 0.4) + ((gf * 3 + ass * 1) / max(1, pv) * 0.5), 2)
        
        evaluations.append({
            "id": pid,
            "nome": nome,
            "ruolo": ruolo,
            "squadra": squadra,
            "Pv": int(pv),
            "Fm_Tot": round(fm_tot, 2),
            "Fm_Recente": round(fm_recent, 2),
            "Delta_Forma": delta_forma,
            "Trend": trend,
            "Score_Potenziale": score_potenziale,
            "Gol": int(gf),
            "Assist": int(ass)
        })
        
    return evaluations

if __name__ == "__main__":
    rosa, storico, df_stats = load_data()
    evals = calculate_player_metrics(rosa, storico, df_stats)
    df_evals = pd.DataFrame(evals)
    print("Valutazione dinamica rosa aggiornata:")
    print(df_evals.sort_values(by="Score_Potenziale", ascending=False))
