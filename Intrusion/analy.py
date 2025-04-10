import re
import requests
import pandas as pd
import time
from dici_country import country_translation, country_code_to_name

# Configurações 
LOG_FILE = 'fw_intrusion.log'
EXCEL_OUTPUT = 'ip_intrusion.xlsx'
TXT_OUTPUT = 'padrão_intrusion.txt'
ABUSEIPDB_API_KEY = "ec6d9e63ebac46d3e6fdb7412c3b5601a02aa040951dccd099d28d65f59ac046c0c05eb293530113"
ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"
MAX_RETRIES = 3

def extrair_ataques(arquivo_log):
    """Extrai ataques e IPs do arquivo de log de intrusão"""
    padrao = r'srcip=([\d.]+).*?attack="([^"]+)"'
    dados = []
    
    try:
        with open(arquivo_log, 'r') as f:
            for linha in f:
                match = re.search(padrao, linha)
                if match:
                    dados.append({
                        'IP': match.group(1),
                        'Ataque': match.group(2)
                    })
        return dados
    except FileNotFoundError:
        print(f"[ERRO] Arquivo {arquivo_log} não encontrado!")
        return []

def verificar_chave_api():
    """Valida a chave API antes de iniciar"""
    if not ABUSEIPDB_API_KEY or ABUSEIPDB_API_KEY == "sua_chave_api_aqui":
        print("\n❌ ERRO: Chave API não configurada!")
        return False
    
    try:
        headers = {'Key': ABUSEIPDB_API_KEY, 'Accept': 'application/json'}
        response = requests.get(f"{ABUSEIPDB_URL}?ipAddress=8.8.8.8&maxAgeInDays=1", 
                              headers=headers, 
                              timeout=10)
        return response.status_code != 401
    except Exception:
        return False

def consultar_abuseipdb(ip, tentativa=1):
    """Consulta com retry automático"""
    headers = {'Key': ABUSEIPDB_API_KEY, 'Accept': 'application/json'}
    params = {'ipAddress': ip, 'maxAgeInDays': '90'}
    
    try:
        response = requests.get(ABUSEIPDB_URL, headers=headers, params=params, timeout=15)
        data = response.json()
        
        country_name = data.get('data', {}).get('countryName')
        country_code = data.get('data', {}).get('countryCode')
        abuse_score = data.get('data', {}).get('abuseConfidenceScore', 0)

        if not country_name and country_code:
            country_name = country_code_to_name.get(country_code, country_code)
        
        return country_translation.get(country_name, country_name) or "Desconhecido", abuse_score
    
    except Exception as e:
        if tentativa < MAX_RETRIES:
            time.sleep(tentativa * 2)
            return consultar_abuseipdb(ip, tentativa + 1)
        return f"Erro: {str(e)[:50]}", 0

def gerar_saidas(dados):
    """Gera os arquivos de saída"""
    # Remove duplicatas mantendo o maior score
    df = pd.DataFrame(dados)
    df_sem_duplicatas = df.sort_values('Abuse Score', ascending=False)\
                         .drop_duplicates(subset=['IP'])\
                         .sort_index()
    
    # Excel com todos os dados
    df.to_excel(EXCEL_OUTPUT, index=False)
    
    # TXT com IPs únicos
    with open(TXT_OUTPUT, 'w', encoding='utf-8') as f:
        ips_unicos = df_sem_duplicatas[['IP', 'Origem']].to_dict('records')
        formato = " | ".join([f"{item['IP']} - {item['Origem']}" for item in ips_unicos])
        f.write(formato)

def main():
    print("=== Iniciando análise de logs de intrusão ===")
    
    if not verificar_chave_api():
        print("Por favor, configure sua chave API corretamente")
        return
    
    ataques = extrair_ataques(LOG_FILE)
    if not ataques:
        print("Nenhum ataque encontrado para análise")
        return
    
    print(f"\n🔍 {len(ataques)} ataques encontrados. Iniciando consultas...")
    
    resultados = []
    for i, item in enumerate(ataques, 1):
        print(f"[{i}/{len(ataques)}] Processando {item['IP']} ({item['Ataque']})...")
        origem, score = consultar_abuseipdb(item['IP'])
        resultados.append({
            'Ataque': item['Ataque'],
            'IP': item['IP'],
            'Origem': origem,
            'Abuse Score': score
        })
        time.sleep(1.5)  # Respeitar rate limit da API
    
    gerar_saidas(resultados)
    print(f"\n✅ Análise concluída! Resultados salvos em:")
    print(f"- {EXCEL_OUTPUT} (todos os dados)")
    print(f"- {TXT_OUTPUT} (IPs únicos)")

if __name__ == "__main__":
    main()