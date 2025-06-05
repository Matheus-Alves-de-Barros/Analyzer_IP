import re
import requests
import pandas as pd
import time
from dici_country import country_translation, country_code_to_name

# Configurações
LOG_FILE = 'fw_vpn.log'
EXCEL_OUTPUT = 'ip_vpn.xlsx'
TXT_OUTPUT = 'padrão_vpn.txt'
ABUSEIPDB_API_KEY = "ec6d9e63ebac46d3e6fdb7412c3b5601a02aa040951dccd099d28d65f59ac046c0c05eb293530113"
ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"
MAX_RETRIES = 3

def extrair_ips(arquivo_log):
    """Extrai usuários e IPs do arquivo de log com padrão corrigido"""
    padrao = r'user="([^"]+)".*?remip=([\d.]+)'
    dados = []
    
    try:
        with open(arquivo_log, 'r') as f:
            for linha in f:
                match = re.search(padrao, linha)
                if match:
                    dados.append({
                        'Usuário': match.group(1), 
                        'IP': match.group(2).strip()  # Remove espaços em branco se houver
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
        ips_unicos = df_sem_duplicatas[['IP', 'País']].to_dict('records')
        formato = " | ".join([f"{item['IP']} - {item['País']}" for item in ips_unicos])
        f.write(formato)

def detectar_padroes_suspeitos(usuario):
    """Detecta padrões suspeitos em nomes de usuário"""
    padroes = [
        (r'^\d+[a-z]+\d+', 'Possível usuário gerado automaticamente'),
        (r'^test$', 'Usuário de teste - potencial força bruta'),
        (r'\.', 'Possível tentativa de credential stuffing')
    ]
    
    for padrao, descricao in padroes:
        if re.search(padrao, usuario):
            return descricao
    return None

def main():
    print("=== Iniciando análise de IPs ===")
    
    if not verificar_chave_api():
        print("Por favor, configure sua chave API corretamente")
        return
    
    ips = extrair_ips(LOG_FILE)
    if not ips:
        print("Nenhum IP encontrado para análise")
        return
    
    print(f"\n� {len(ips)} IPs encontrados. Iniciando consultas...")
    
    resultados = []
    for i, item in enumerate(ips, 1):
        print(f"[{i}/{len(ips)}] Processando {item['IP']}...")
        pais, score = consultar_abuseipdb(item['IP'])
        alerta = detectar_padroes_suspeitos(item['Usuário'])
        
        resultados.append({
            'Usuário': item['Usuário'],
            'IP': item['IP'],
            'País': pais,
            'Abuse Score': score,
            'Alerta': alerta or 'Nenhum'
        })
        time.sleep(1.5)  # Respeita o rate limit da API
    
    gerar_saidas(resultados)
    print(f"\n✅ Análise concluída! Resultados salvos em:")
    print(f"- {EXCEL_OUTPUT} (todos os dados)")
    print(f"- {TXT_OUTPUT} (IPs únicos)")

if __name__ == "__main__":
    main()
