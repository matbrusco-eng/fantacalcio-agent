import requests
import pandas as pd
import io

URL_EXCEL_STATS = "https://www.fantacalcio.it/api/v1/Excel/stats/21/5"

def test_estrazione_fantamedia():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    print("📡 Scaricamento file Excel da Fantacalcio.it...")
    resp = requests.get(URL_EXCEL_STATS, headers=headers)
    
    if resp.status_code != 200:
        print(f"❌ Errore durante il download. Status Code: {resp.status_code}")
        return

    print("✅ Download completato! Lettura del file Excel...")
    
    try:
        # Carichiamo il file Excel in memoria
        excel_data = io.BytesIO(resp.content)
        df = pd.read_excel(excel_data, header=1) # Di solito la prima riga è il titolo
        
        print(f"📊 Colonne trovate nell'Excel: {list(df.columns)}")
        print("\n🔍 Prime 5 righe della tabella:")
        print(df.head())
        
    except Exception as e:
        print(f"❌ Errore nella lettura del file Excel: {e}")

if __name__ == "__main__":
    test_estrazione_fantamedia()
