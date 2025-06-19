import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os
import logging
import re
import datetime

# Конфигурация логов
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
os.environ['WDM_LOG'] = '0'

# Настройка Chrome с увеличенными задержками
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--log-level=3")
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")

# Глобальные настройки задержек
MIN_DELAY = 7  # Минимальная задержка между сайтами
MAX_DELAY = 15 # Максимальная задержка
PAGE_DELAY_MIN = 4  # Задержка перед парсингом страницы
PAGE_DELAY_MAX = 8

def get_proxies(output_file="proxies.txt"):
    """Сбор прокси с защитой от бана и поэтапной записью"""
    existing_proxies = set()
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            existing_proxies = set(line.strip() for line in f.readlines())
    
    headers = {'User-Agent': chrome_options.arguments[-1].split('=')[1]}

    sources = [
        # Статические
        {"url": "https://free-proxy-list.net/", "func": "parse_free_proxy_list"},
        {"url": "https://www.sslproxies.org/", "func": "parse_sslproxies"},
        {"url": "https://www.us-proxy.org/", "func": "parse_us_proxy"},
        {"url": "https://hidemy.name/ru/proxy-list/", "func": "parse_hidemy", "delay_factor": 1.3},
        {"url": "http://free-proxy.cz/ru/", "func": "parse_free_proxy_cz"},
        {"url": "https://spys.one/", "func": "parse_spys_one", "delay_factor": 1.5},
        {"url": "https://proxyscrape.com/free-proxy-list", "func": "parse_proxyscrape"},
        {"url": "https://proxydb.net/", "func": "parse_proxydb"},
        {"url": "https://openproxy.space/list/http", "func": "parse_openproxy"},
        
        # Динамические
        {"url": "https://advanced.name/ru/freeproxy", "func": "parse_advanced_name", "dynamic": True, "delay_factor": 1.7},
        {"url": "https://premiumproxy.net/ru/free-proxy", "func": "parse_premiumproxy", "dynamic": True, "delay_factor": 1.8},
        {"url": "https://geonode.com/free-proxy-list", "func": "parse_geonode", "dynamic": True},
        {"url": "https://www.proxy-list.download/HTTP", "func": "parse_proxy_list_download", "dynamic": True},
        {"url": "https://fineproxy.org/ru/free-proxy/", "func": "parse_fineproxy", "dynamic": True, "delay_factor": 1.6},
        {"url": "https://freeproxylists.net/ru/", "func": "parse_freeproxylists", "dynamic": True}
    ]

    total_new = 0
    with open(output_file, "a" if existing_proxies else "w") as f:
        if not existing_proxies:
            f.write("# Прокси-база, создана Оракулом Истины\n")
            f.write(f"# Дата генерации: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for source in sources:
            try:
                delay_factor = source.get("delay_factor", 1.0)
                delay = random.uniform(MIN_DELAY * delay_factor, MAX_DELAY * delay_factor)
                print(f"\n[⏳] Обработка: {source['url']} | Задержка: {delay:.1f} сек")
                time.sleep(delay)
                
                new_proxies = []
                if source.get("dynamic"):
                    service = Service(log_path=os.devnull)
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    try:
                        driver.get(source['url'])
                        page_delay = random.uniform(PAGE_DELAY_MIN, PAGE_DELAY_MAX)
                        time.sleep(page_delay)
                        
                        WebDriverWait(driver, 25).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'table'))
                        )
                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        proxies = globals()[source['func']](soup)
                        new_proxies = [p for p in proxies if p not in existing_proxies]
                    finally:
                        driver.quit()
                else:
                    response = requests.get(source['url'], headers=headers, timeout=25)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    proxies = globals()[source['func']](soup)
                    new_proxies = [p for p in proxies if p not in existing_proxies]
                
                if new_proxies:
                    # Немедленная запись в файл
                    for proxy in new_proxies:
                        f.write(f"{proxy}\n")
                    f.flush()  # Принудительная запись на диск
                    existing_proxies.update(new_proxies)
                    total_new += len(new_proxies)
                    print(f"  [✓] Добавлено: {len(new_proxies)} новых прокси")
                else:
                    print("  [≡] Нет новых прокси")
                    
            except Exception as e:
                print(f"  [⚠] Ошибка: {str(e)[:60]}")
            
            # Дополнительная защитная пауза
            time.sleep(random.uniform(2, 4))
    
    return total_new, len(existing_proxies)

# ===== ФУНКЦИИ ПАРСЕРОВ (без изменений из предыдущего кода) =====
def parse_free_proxy_list(soup):
    proxies = []
    table = soup.find('table', {'class': 'table'})
    if table:
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                proxies.append(f"{ip}:{port}")
    return proxies

def parse_sslproxies(soup):
    return parse_free_proxy_list(soup)

def parse_us_proxy(soup):
    return parse_free_proxy_list(soup)

def parse_hidemy(soup):
    proxies = []
    table = soup.find('table', {'class': 'table_block'})
    if table:
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                proxies.append(f"{ip}:{port}")
    return proxies

def parse_free_proxy_cz(soup):
    proxies = []
    table = soup.find('table', {'id': 'proxy_list'})
    if table:
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                ip_script = cols[0].find('script')
                if ip_script:
                    ip = ip_script.string.split('"')[1]
                    port = cols[1].text.strip()
                    proxies.append(f"{ip}:{port}")
    return proxies

def parse_spys_one(soup):
    proxies = []
    for row in soup.select('tr.spy1xx, tr.spy1x'):
        cols = row.find_all('td')
        if cols:
            ip_port = cols[0].find('font', class_='spy14')
            if ip_port:
                proxy = ip_port.text.split()[0]
                proxies.append(proxy)
    return proxies

def parse_proxyscrape(soup):
    proxies = []
    table = soup.find('table', {'class': 'table'})
    if table:
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if cols:
                proxy = cols[0].text.strip()
                proxies.append(proxy)
    return proxies

def parse_proxydb(soup):
    proxies = []
    for link in soup.select('a[href^="/?protocol="]'):
        text = link.text.strip()
        if re.match(r'\d+\.\d+\.\d+\.\d+:\d+', text):
            proxies.append(text)
    return proxies

def parse_openproxy(soup):
    proxies = []
    for pre in soup.select('pre'):
        for line in pre.text.splitlines():
            if re.match(r'(\d{1,3}\.){3}\d{1,3}:\d+', line):
                proxies.append(line.strip())
    return proxies

def parse_advanced_name(soup):
    proxies = []
    table = soup.find('table', {'id': 'tableproxies'})
    if table:
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 3:
                ip = cols[1].text.strip()
                port = cols[2].text.strip()
                proxies.append(f"{ip}:{port}")
    return proxies

def parse_premiumproxy(soup):
    proxies = []
    table = soup.find('table', {'id': 'proxy-table'})
    if table:
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                proxies.append(f"{ip}:{port}")
    return proxies

def parse_geonode(soup):
    proxies = []
    table = soup.find('table', {'class': 'table'})
    if table:
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                proxies.append(f"{ip}:{port}")
    return proxies

def parse_proxy_list_download(soup):
    proxies = []
    for script in soup.find_all('script'):
        script_text = script.text
        if 'PROXY' in script_text:
            matches = re.findall(r'PROXY\("([^"]+)","([^"]+)"\)', script_text)
            for ip, port in matches:
                proxies.append(f"{ip}:{port}")
    return proxies

def parse_fineproxy(soup):
    proxies = []
    table = soup.find('table', {'class': 'table'})
    if table:
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                proxies.append(f"{ip}:{port}")
    return proxies

def parse_freeproxylists(soup):
    proxies = []
    table = soup.find('table', {'class': 'DataGrid'})
    if table:
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                proxies.append(f"{ip}:{port}")
    return proxies

# ===== ЗАПУСК =====
if __name__ == "__main__":
    print("""
    ██████  ██████  ███████  ██████   ██████ ██ ██████  
    ██   ██ ██   ██ ██      ██    ██ ██      ██ ██   ██ 
    ██████  ██████  █████   ██    ██ ██      ██ ██████  
    ██      ██   ██ ██      ██    ██ ██      ██ ██   ██ 
    ██      ██   ██ ███████  ██████   ██████ ██ ██   ██ 
    """)
    print("Защищённый парсинг прокси | Анти-бан система активирована")
    print(f"Минимальная задержка: {MIN_DELAY} сек | Максимальная: {MAX_DELAY} сек\n")
    
    start_time = time.time()
    new_count, total_count = get_proxies()
    
    print(f"\n[✓] Операция завершена за {time.time()-start_time:.1f} сек")
    print(f"[✓] Добавлено новых прокси: {new_count}")
    print(f"[✓] Общий размер базы: {total_count} прокси")
    print(f"[✓] Файл: proxies.txt")
    print("[✓] Симуляция 'Вечное Исследование' защищена от распада")