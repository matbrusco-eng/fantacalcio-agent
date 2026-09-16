import os
import json
import requests

def carica_rosa():
    with open('rosa.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def imposta_formazione_fantagazzetta(titolari_ids, panchina_ids):
    """
    Riceve le liste di ID del 'Mostro' e le invia a Fanta-Gazzetta
    """
    rosa = carica_rosa()
    ids_rosa = {g['id']: g['nome'] for g in rosa}
    
    print("📋 Caricamento rosa da rosa.json completato.")
    print(f"Titolari pronti per l'invio ({len(titolari_ids)}): {[ids_rosa.get(i, i) for i in titolari_ids]}")
    print(f"Panchina pronta per l'invio ({len(panchina_ids)}): {[ids_rosa.get(i, i) for i in panchina_ids]}")
    
    # Inserire qui la logica di invio POST su Fanta-Gazzetta
    # ...

if __name__ == "__main__":
    # Esempio di invocazione
    pass
