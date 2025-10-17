import re
import os
import time
import json
import requests
import pandas as pd
from typing import List, Dict, Tuple

# Configurações (chave via variável de ambiente)
LOG_FILE = 'fw_intrusion.log'
EXCEL_OUTPUT = 'ip_intrusion.xlsx'
TXT_OUTPUT = 'padrao_intrusion.txt'
ABUSEIPDB_API_KEY = os.environ.get("ec6d9e63ebac46d3e6fdb7412c3b5601a02aa040951dccd099d28d65f59ac046c0c05eb293530113")  # set via env var
ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15
RATE_SLEEP = 1.5  # sleep entre consultas (ajuste conforme limitações da API)

def parse_fortinet_line(line: str) -> Dict[str, str]:
    """
    Parse genérico para linhas de Fortinet: captura pares chave="valor" ou chave=valor
    Retorna um dict com as chaves encontradas.
    """
    pattern = re.compile(r'(\w+)="([^"]*)"|(\w+)=([^\s]+)')
    data = {}
    for m in pattern.finditer(line):
        if m.group(1):
            data[m.group(1)] = m.group(2)
        else:
            key, val = m.group(3), m.group(4)
            # remove aspas residuais
            data[key] = val.strip('"')
    return data

def extrair_ataques(arquivo_log: str) -> List[Dict[str, str]]:
    """Extrai ataques e IPs do arquivo de log Fortinet (mais robusto)."""
    resultados = []
    try:
        with open(arquivo_log, 'r', encoding='utf-8') as f:
            for linha in f:
                parsed = parse_fortinet_line(linha)
                if 'srcip' in parsed and 'attack' in parsed:
                    resultados.append({
                        'IP': parsed.get('srcip'),
                        'Ataque': parsed.get('attack'),
                        'OrigemLog': parsed.get('srccountry', ''),
                        'URL': parsed.get('url', ''),
                        'SrcPort': parsed.get('srcport', '')
                    })
        return resultados
    except FileNotFoundError:
        print(f"[ERRO] Arquivo {arquivo_log} não encontrado!")
        return []

def verificar_chave_api() -> bool:
    if not ABUSEIPDB_API_KEY:
        print("❌ ERRO: ABUSEIPDB_API_KEY não configurada (use variável de ambiente).")
        return False
    return True

def consultar_abuseipdb(ip: str, session: requests.Session, tentativa: int = 1) -> Tuple[str, int]:
    """
    Consulta AbuseIPDB com tratamento de status e retry/backoff.
    Retorna (OrigemDetectadaOuMensagem, abuse_score)
    """
    headers = {'Key': ABUSEIPDB_API_KEY, 'Accept': 'application/json'}
    params = {'ipAddress': ip, 'maxAgeInDays': 90}
    try:
        resp = session.get(ABUSEIPDB_URL, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json().get('data', {})
            country = data.get('countryName') or data.get('countryCode') or ''
            score = data.get('abuseConfidenceScore', 0)
            return country or "Desconhecido", int(score or 0)
        elif resp.status_code == 401:
            return "API Key Inválida", 0
        elif resp.status_code == 429:
            # rate limit: aumentar backoff e tentar de novo (até MAX_RETRIES)
            if tentativa < MAX_RETRIES:
                sleep_time = 2 ** tentativa
                print(f"[WARN] 429 rate limit para {ip}. Dormindo {sleep_time}s e tentando {tentativa+1}/{MAX_RETRIES}")
                time.sleep(sleep_time)
                return consultar_abuseipdb(ip, session, tentativa + 1)
            return "RateLimit", 0
        else:
            # outros códigos: retornar mensagem
            return f"HTTP {resp.status_code}", 0
    except requests.RequestException as e:
        if tentativa < MAX_RETRIES:
            time.sleep(2 ** tentativa)
            return consultar_abuseipdb(ip, session, tentativa + 1)
        return f"ErroReq: {str(e)[:80]}", 0

def gerar_saidas(resultados: List[Dict[str, object]]):
    df = pd.DataFrame(resultados)
    if df.empty:
        print("[INFO] Sem resultados para salvar.")
        return

    # Salva todos os dados no Excel
    df.to_excel(EXCEL_OUTPUT, index=False)

    # Deduplicar mantendo maior Abuse Score por IP
    if 'Abuse Score' in df.columns:
        df_best = df.loc[df.groupby('IP')['Abuse Score'].idxmax()].reset_index(drop=True)
    else:
        df_best = df.drop_duplicates(subset=['IP']).reset_index(drop=True)

    # Salva TXT com uma linha por IP
    with open(TXT_OUTPUT, 'w', encoding='utf-8') as f:
        for _, row in df_best.iterrows():
            linha = f"{row.get('IP')} - {row.get('Origem')} - Score:{row.get('Abuse Score', 'N/A')}\n"
            f.write(linha)

    print(f"[OK] Arquivos gerados: {EXCEL_OUTPUT}, {TXT_OUTPUT}")

def main():
    print("=== Iniciando análise de logs de intrusão ===")
    if not verificar_chave_api():
        return

    ataques = extrair_ataques(LOG_FILE)
    if not ataques:
        print("Nenhum ataque encontrado para análise")
        return

    print(f"🔍 {len(ataques)} entradas extraídas. Iniciando consultas AbuseIPDB...")

    session = requests.Session()
    resultados = []
    for i, item in enumerate(ataques, start=1):
        ip = item['IP']
        print(f"[{i}/{len(ataques)}] {ip} -> {item['Ataque']}")
        origem_api, score = consultar_abuseipdb(ip, session)
        # preferir origem do log se não houver dado da API
        origem_final = item.get('OrigemLog') or origem_api or "Desconhecido"
        resultados.append({
            'Ataque': item['Ataque'],
            'IP': ip,
            'Origem': origem_final,
            'Abuse Score': score,
            'URL': item.get('URL', ''),
            'SrcPort': item.get('SrcPort', '')
        })
        time.sleep(RATE_SLEEP)

    gerar_saidas(resultados)
    print("✅ Análise concluída!")

if __name__ == "__main__":
    main()
