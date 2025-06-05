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
    """Extrai usuários e IPs do arquivo de log com padrão robusto"""
    # Padrão otimizado para os logs fornecidos
    padrao = r'user="([^"]+)".*?remip=([\d.]+)\s'
    dados = []
    
    try:
        with open(arquivo_log, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            
            # Verifica se o arquivo não está vazio
            if not conteudo.strip():
                print("[AVISO] Arquivo de log está vazio!")
                return []
            
            # Encontra todos os matches
            matches = re.finditer(padrao, conteudo, re.DOTALL)
            
            for match in matches:
                dados.append({
                    'Usuário': match.group(1).strip(),
                    'IP': match.group(2).strip()
                })
                
        if not dados:
            print("[AVISO] Nenhum IP encontrado. Verifique o formato do log.")
            # Debug: Mostrar primeiras linhas do log
            with open(arquivo_log, 'r', encoding='utf-8') as f:
                print("\nExemplo das primeiras linhas do log:")
                for i, linha in enumerate(f):
                    if i < 5:
                        print(linha.strip())
                    else:
                        break
        
        return dados
    
    except FileNotFoundError:
        print(f"[ERRO] Arquivo {arquivo_log} não encontrado!")
        return []
    except Exception as e:
        print(f"[ERRO] Erro ao ler arquivo: {str(e)}")
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
    except Exception as e:
        print(f"[ERRO] Falha na verificação da API: {str(e)}")
        return False

def consultar_abuseipdb(ip, tentativa=1):
    """Consulta com retry automático"""
    headers = {'Key': ABUSEIPDB_API_KEY, 'Accept': 'application/json'}
    params = {'ipAddress': ip, 'maxAgeInDays': '90'}
    
    try:
        response = requests.get(ABUSEIPDB_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
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
        print(f"[ERRO] Falha ao consultar IP {ip}: {str(e)[:100]}")
        return f"Erro: {str(e)[:50]}", 0

def gerar_saidas(dados):
    """Gera os arquivos de saída"""
    try:
        df = pd.DataFrame(dados)
        
        if df.empty:
            print("[AVISO] Nenhum dado para gerar saída!")
            return
        
        # Remove duplicatas mantendo o maior score
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
            
    except Exception as e:
        print(f"[ERRO] Falha ao gerar saídas: {str(e)}")

def main():
    print("=== Iniciando análise de IPs ===")
    
    if not verificar_chave_api():
        print("Por favor, configure sua chave API corretamente")
        return
    
    print(f"\nLendo arquivo de log: {LOG_FILE}")
    ips = extrair_ips(LOG_FILE)
    
    if not ips:
        print("Nenhum IP encontrado para análise. Verifique:")
        print(f"1. O arquivo {LOG_FILE} existe e tem conteúdo")
        print("2. O formato do log corresponde ao esperado")
        print("3. Os logs contêm os campos 'user' e 'remip'")
        return
    
    print(f"\n� {len(ips)} IPs encontrados. Iniciando consultas à AbuseIPDB...")
    
    resultados = []
    for i, item in enumerate(ips, 1):
        print(f"[{i}/{len(ips)}] Processando {item['IP']} (usuário: {item['Usuário']})...")
        pais, score = consultar_abuseipdb(item['IP'])
        resultados.append({
            'Usuário': item['Usuário'],
            'IP': item['IP'],
            'País': pais,
            'Abuse Score': score
        })
        time.sleep(1.5)  # Respeita o rate limit da API
    
    gerar_saidas(resultados)
    print(f"\n✅ Análise concluída! Resultados salvos em:")
    print(f"- {EXCEL_OUTPUT} (todos os dados)")
    print(f"- {TXT_OUTPUT} (IPs únicos)")

if __name__ == "__main__":
    main()
