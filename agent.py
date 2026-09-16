import os
import json

def carica_rosa():
    with open('rosa.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def imposta_formazione_fantagazzetta(titolari_ids, panchina_ids):
    """
    Riceve le liste di ID generate dall'algoritmo e le gestisce
    per la successiva integrazione con l'invio su Fanta-Gazzetta.
    """
    rosa = carica_rosa()
    ids_rosa = {g['id']: g['nome'] for g in rosa}
    
    print("📋 Rosa caricata con successo da rosa.json.")
    print(f"Titolari pronti ({len(titolari_ids)}): {[ids_rosa.get(i, i) for i in titolari_ids]}")
    print(f"Panchina pronta ({len(panchina_ids)}): {[ids_rosa.get(i, i) for i in panchina_ids]}")

if __name__ == "__main__":
    pass
