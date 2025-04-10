import re
import requests
import pandas as pd
import time
from collections import defaultdict
from dici_country import country_translation, country_code_to_name

# Configurações
LOG_FILE = 'fw_analyzer.log'
EXCEL_OUTPUT = 'fortiweb_attack_report.xlsx'
TXT_OUTPUT = 'ips_analyzer.txt'
ABUSEIPDB_API_KEY = "ec6d9e63ebac46d3e6fdb7412c3b5601a02aa040951dccd099d28d65f59ac046c0c05eb293530113"
ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"
MAX_RETRIES = 3

def extrair_ataques_fortiweb(arquivo_log):
    """Extrai IPs, main_type e outros campos relevantes"""
    padrao = r'src="([\d.]+)".*?main_type="([^"]+)"'
    dados = []

    try:
        with open(arquivo_log, 'r', encoding='utf-8') as f:
            for linha in f:
                match = re.search(padrao, linha)
                if match:
                    dados.append({
                        'IP': match.group(1),
                        'Main-Type': match.group(2)
                    })
        return dados
    except FileNotFoundError:
        print(f"[ERRO] Arquivo {arquivo_log} não encontrado!")
        return []

def consultar_abuseipdb(ip, tentativa=1):
    """Consulta o AbuseIPDB"""
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

def categorizar_ips(dados):
    """Separa IPs em categorias baseadas no Main-Type"""
    categorias = {
        'Known Bots Detection': [],
        'Signature Detection': [],
        'Outros': []
    }

    for item in dados:
        ip_info = f"{item['IP']} - {item['Origem']} (Score: {item['Abuse Score']})"

        if 'Known Bots' in item['Main-Type']:
            categorias['Known Bots Detection'].append(ip_info)
        elif 'Signature' in item['Main-Type']:
            categorias['Signature Detection'].append(ip_info)
        else:
            categorias['Outros'].append(ip_info)

    return categorias

def gerar_relatorios(dados, categorias):
    """Gera Excel e arquivo TXT categorizado"""
    df = pd.DataFrame(dados)

    # Remove duplicados mantendo o maior Abuse Score
    df_sem_duplicatas = df.sort_values('Abuse Score', ascending=False)\
                         .drop_duplicates(subset=['IP'])\
                         .sort_index()

    # Estatísticas por tipo de ataque
    stats = defaultdict(int)
    for item in dados:
        stats[item['Main-Type']] += 1
    df_stats = pd.DataFrame.from_dict(stats, orient='index', columns=['Count'])\
                          .sort_values('Count', ascending=False)

    # Salva em Excel (2 abas)
    with pd.ExcelWriter(EXCEL_OUTPUT) as writer:
        df.to_excel(writer, sheet_name='Detalhes', index=False)
        df_stats.to_excel(writer, sheet_name='Estatísticas')

    # Salva IPs categorizados em TXT
    with open(TXT_OUTPUT, 'w', encoding='utf-8') as f:
        f.write("=== KNOWN BOTS DETECTION ===\n")
        f.write("\n".join(categorias['Known Bots Detection']) + "\n\n")

        f.write("=== SIGNATURE DETECTION ===\n")
        f.write("\n".join(categorias['Signature Detection']) + "\n\n")

        f.write("=== OUTROS TIPOS ===\n")
        f.write("\n".join(categorias['Outros']))

def main():
    print("=== Análise de Logs FortiWeb ===")

    ataques = extrair_ataques_fortiweb(LOG_FILE)
    if not ataques:
        print("Nenhum ataque encontrado para análise")
        return

    print(f"\n🔍 {len(ataques)} ataques encontrados. Consultando AbuseIPDB...")

    resultados = []
    for i, item in enumerate(ataques, 1):
        print(f"[{i}/{len(ataques)}] Processando {item['IP']}...")
        origem, score = consultar_abuseipdb(item['IP'])
        resultados.append({
            'IP': item['IP'],
            'Main-Type': item['Main-Type'],
            'Origem': origem,
            'Abuse Score': score
        })
        time.sleep(1.5)  # Respeitar rate limit

    # Categoriza os IPs antes de gerar relatórios
    ips_categorizados = categorizar_ips(resultados)
    gerar_relatorios(resultados, ips_categorizados)

    print(f"\n✅ Relatório gerado:")
    print(f"- {EXCEL_OUTPUT} (detalhes + estatísticas)")
    print(f"- {TXT_OUTPUT} (IPs categorizados)")

if __name__ == "__main__":
    main()
