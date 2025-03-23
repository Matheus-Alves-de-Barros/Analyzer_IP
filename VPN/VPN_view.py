import re
import requests
import pandas as pd
from openpyxl import Workbook

# Caminhos
LOG = 'fw_vpn.log'
EXCEL = 'dados.xlsx'
FORMAT = 'ips_form.txt'
ABUSEIPDB_API_KEY = "ec6d9e63ebac46d3e6fdb7412c3b5601a02aa040951dccd099d28d65f59ac046c0c05eb293530113"
ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"

# Dicionário para traduzir nomes de países
country_translation = {
    "Afghanistan": "Afeganistão",
    "South Africa": "África do Sul",
    "Albania": "Albânia",
    "Germany": "Alemanha",
    "Andorra": "Andorra",
    "Angola": "Angola",
    "Antigua and Barbuda": "Antígua e Barbuda",
    "Saudi Arabia": "Arábia Saudita",
    "Algeria": "Argélia",
    "Argentina": "Argentina",
    "Armenia": "Armênia",
    "Australia": "Austrália",
    "Austria": "Áustria",
    "Azerbaijan": "Azerbaijão",
    "Bahamas": "Bahamas",
    "Bahrain": "Bahrein",
    "Bangladesh": "Bangladesh",
    "Barbados": "Barbados",
    "Belize": "Belize",
    "Benin": "Benim",
    "Belarus": "Bielorrússia",
    "Bolivia": "Bolívia",
    "Bosnia and Herzegovina": "Bósnia e Herzegovina",
    "Botswana": "Botsuana",
    "Brazil": "Brasil",
    "Brunei": "Brunei",
    "Bulgaria": "Bulgária",
    "Burkina Faso": "Burkina Faso",
    "Burundi": "Burundi",
    "Bhutan": "Butão",
    "Cape Verde": "Cabo Verde",
    "Cameroon": "Camarões",
    "Cambodia": "Camboja",
    "Canada": "Canadá",
    "Qatar": "Catar",
    "Kazakhstan": "Cazaquistão",
    "Chad": "Chade",
    "Chile": "Chile",
    "China": "China",
    "Cyprus": "Chipre",
    "Colombia": "Colômbia",
    "Comoros": "Comores",
    "Congo": "Congo",
    "Costa Rica": "Costa Rica",
    "Croatia": "Croácia",
    "Cuba": "Cuba",
    "Curacao": "Curaçau",
    "Denmark": "Dinamarca",
    "Djibouti": "Djibuti",
    "Dominica": "Dominica",
    "Egypt": "Egito",
    "El Salvador": "El Salvador",
    "Ecuador": "Equador",
    "Eritrea": "Eritreia",
    "Slovakia": "Eslováquia",
    "Slovenia": "Eslovênia",
    "Spain": "Espanha",
    "United States": "Estados Unidos",
    "Estonia": "Estônia",
    "Eswatini": "Eswatini",
    "Ethiopia": "Etiópia",
    "Fiji": "Fiji",
    "Philippines": "Filipinas",
    "Finland": "Finlândia",
    "France": "França",
    "Gabon": "Gabão",
    "Gambia": "Gâmbia",
    "Ghana": "Gana",
    "Greece": "Grécia",
    "Grenada": "Granada",
    "Guatemala": "Guatemala",
    "Guinea": "Guiné",
    "Guinea-Bissau": "Guiné-Bissau",
    "Guyana": "Guiana",
    "Haiti": "Haiti",
    "Honduras": "Honduras",
    "Hungary": "Hungria",
    "Yemen": "Iémen",
    "Marshall Islands": "Ilhas Marshall",
    "Solomon Islands": "Ilhas Salomão",
    "India": "Índia",
    "Indonesia": "Indonésia",
    "Iran": "Irã",
    "Iraq": "Iraque",
    "Ireland": "Irlanda",
    "Iceland": "Islândia",
    "Israel": "Israel",
    "Italy": "Itália",
    "Jamaica": "Jamaica",
    "Japan": "Japão",
    "Jordan": "Jordânia",
    "Kiribati": "Kiribati",
    "Kosovo": "Kosovo",
    "Kuwait": "Kuwait",
    "Laos": "Laos",
    "Lesotho": "Lesoto",
    "Latvia": "Letônia",
    "Lebanon": "Líbano",
    "Liberia": "Libéria",
    "Libya": "Líbia",
    "Liechtenstein": "Liechtenstein",
    "Lithuania": "Lituânia",
    "Luxembourg": "Luxemburgo",
    "North Macedonia": "Macedônia do Norte",
    "Madagascar": "Madagascar",
    "Malaysia": "Malásia",
    "Malawi": "Maláui",
    "Maldives": "Maldivas",
    "Mali": "Mali",
    "Malta": "Malta",
    "Morocco": "Marrocos",
    "Mauritius": "Maurício",
    "Mauritania": "Mauritânia",
    "Mexico": "México",
    "Micronesia": "Micronésia",
    "Mozambique": "Moçambique",
    "Moldova": "Moldávia",
    "Monaco": "Mônaco",
    "Mongolia": "Mongólia",
    "Montenegro": "Montenegro",
    "Namibia": "Namíbia",
    "Nauru": "Nauru",
    "Nepal": "Nepal",
    "Nicaragua": "Nicarágua",
    "Niger": "Níger",
    "Nigeria": "Nigéria",
    "Norway": "Noruega",
    "New Zealand": "Nova Zelândia",
    "Oman": "Omã",
    "Netherlands": "Países Baixos",
    "Palau": "Palau",
    "Panama": "Panamá",
    "Papua New Guinea": "Papua-Nova Guiné",
    "Pakistan": "Paquistão",
    "Paraguay": "Paraguai",
    "Peru": "Peru",
    "Poland": "Polônia",
    "Portugal": "Portugal",
    "Kenya": "Quênia",
    "Central African Republic": "República Centro-Africana",
    "Czech Republic": "República Checa",
    "Republic of the Congo": "República do Congo",
    "Dominican Republic": "República Dominicana",
    "Rwanda": "Ruanda",
    "Romania": "Romênia",
    "Russia": "Rússia",
    "San Marino": "São Marino",
    "Saint Kitts and Nevis": "São Cristóvão e Nevis",
    "São Tomé and Príncipe": "São Tomé e Príncipe",
    "Senegal": "Senegal",
    "Sierra Leone": "Serra Leoa",
    "Syria": "Síria",
    "Singapore": "Singapura",
    "Somalia": "Somália",
    "Sri Lanka": "Sri Lanka",
    "Swaziland": "Suazilândia",
    "Sudan": "Sudão",
    "South Sudan": "Sudão do Sul",
    "Suriname": "Suriname",
    "Sweden": "Suécia",
    "Switzerland": "Suíça",
    "Tanzania": "Tanzânia",
    "Togo": "Togo",
    "Tonga": "Tonga",
    "Trinidad and Tobago": "Trinidad e Tobago",
    "Tunisia": "Tunísia",
    "Turkmenistan": "Turcomenistão",
    "Turkey": "Turquia",
    "Tuvalu": "Tuvalu",
    "Uganda": "Uganda",
    "Ukraine": "Ucrânia",
    "Uruguay": "Uruguai",
    "Vanuatu": "Vanuatu",
    "Vatican City": "Vaticano",
    "Venezuela": "Venezuela",
    "Vietnam": "Vietnã",
    "Zambia": "Zâmbia",
    "Zimbabwe": "Zimbábue"
}

# Função para consultar o AbusedIP
def abused(ip):
    headers = {
        'Key': ABUSEIPDB_API_KEY,
        'Accept': 'application/json'
    }
    params = {
        'ipAddress': ip,
        'maxAgeInDays': '90'
    }
    try:
        response = requests.get(ABUSEIPDB_URL, headers=headers, params=params)
        data = response.json()
        country = data.get('data', {}).get('countryName', 'Desconhecido')
        abuse_score = data.get('data', {}).get('abuseConfidenceScore', 'N/A')
        return country_translation.get(country, country), abuse_score
    except Exception as e:
        print(f"Erro ao consultar IP {ip}: {e}")
        return "Erro", "N/A"

# Extraindo Dados
def extraindo_ips(LOG):
    dados = []
    with open(LOG, 'r') as arquivo:
        for linha in arquivo:
            match = re.search(r'user="([^"]+)"\s+remip=([\d.]+)', linha)
            if match:
                user, ip = match.groups()
                dados.append({'Usuário': user, 'IP': ip})
    return dados

# Função para salvar na planilha
def excel(dados, EXCEL):
    df = pd.DataFrame(dados)
    df.to_excel(EXCEL, index=False)
    print(f"Planilha salva em {EXCEL}")

# Função para gerar o arquivo .txt
def gerar_txt(dados, FORMAT):
    formato = " | ".join([f"{entry['IP']} - {entry['País']}" for entry in dados])
    with open(FORMAT, 'w', encoding='utf-8') as arquivo:
        arquivo.write(formato)
    print(f"Arquivo txt gerado em {FORMAT}")

# Execução do programa
if __name__ == "__main__":
    # Extraindo dados
    dados_log = extraindo_ips(LOG)
    print(f"Dados extraídos de {LOG}")

    # Consultando IPs
    for entry in dados_log:
        ip = entry["IP"]
        country, abuse_score = abused(ip)
        entry['País'] = country
        entry['Abuse Score'] = abuse_score

    # Salvando na planilha
    excel(dados_log, EXCEL)

    # Gerando txt
    gerar_txt(dados_log, FORMAT)