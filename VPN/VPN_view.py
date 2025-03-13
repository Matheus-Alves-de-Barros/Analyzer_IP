import re
import requests
import pandas as pd

ABUSEIPDB_API_KEY = "ec6d9e63ebac46d3e6fdb7412c3b5601a02aa040951dccd099d28d65f59ac046c0c05eb293530113"
ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"

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


def get_country(ip):
    headers = {
        "Key": ABUSEIPDB_API_KEY,
        "Accept": "application/json"
    }
    params = {
        "ipAddress": ip,
        "verbose": "true"
    }
    try:
        response = requests.get(ABUSEIPDB_URL, headers=headers, params=params)
        data = response.json()

        country = data.get("data", {}).get("countryName", "Desconhecido")
        abuse_score = data.get("data", {}).get("abuseConfidenceScore", "N/A")

        return country_translation.get(country, country), abuse_score
    except Exception as e:
        print(f"Erro ao buscar IP {ip}: {e}")
        return "Erro", "N/A"


log_file = "fw_vpn.log"
with open(log_file, "r") as file:
    log_data = file.readlines()


pattern = re.compile(r'user="([^"]+)"\s+remip=([\d.]+)')

entries = []
for line in log_data:
    match = pattern.search(line)
    if match:
        user, ip = match.groups()
        country, abuse_score = get_country(ip)
        entries.append({"Usuário": user, "IP": ip, "País": country, "Abuse Score": abuse_score})


df = pd.DataFrame(entries)
df.to_excel("ips_vpn.xlsx", index=False)

print("Arquivo gerado: ips.xlsx")

def format_envio(ip_vpn.xlsx, envio_plan.txt)
    with open(ip_vpn.xlsx, "r", encoding="utf-8") as file:
        linhas = [linha.strip().split(maxsplit=1) for linha in file if linha.strip()]

    resultado = " | ".join([f"{ip} - {pais}" for ip, pais in linhas])

    with open(envio_plan, "w", encoding="utf-8") as file:
        file.write(resultado)

formatar_ips("ip_vpn.txt", "envio_plan.txt")