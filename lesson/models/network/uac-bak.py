import requests
import urllib3
import base64


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.config import Config
from sendqueue import send_text
# send_text = print

c_path = "D:/sofe/chrome/chrome-win64/chrome.exe"
d_path = "D:/sofe/chrome/chromedriver-win64/chromedriver.exe"
# c_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# d_path = "/Applications/Google Chrome.app/Contents/MacOS/chromedriver"

uac_conf = Config().get_config("uac", "network.yaml")
url = uac_conf["url"]
user = uac_conf["user"]
pwd = uac_conf["pwd"]


# Function to initialize Selenium driver
def init_driver(chrome_binary_path=c_path, chromedriver_path=d_path):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Use new headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "--disable-blink-features=AutomationControlled"
    )  # Hide automation
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.7151.69 Safari/537.36"
    )
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "--disable-devtools"
    )  # Disable DevTools to prevent debugging
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")

    # Specify the Chrome binary location
    chrome_options.binary_location = chrome_binary_path

    try:
        # Use Service for Selenium 4+
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        # Remove automation flags and disable debugger
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        driver.execute_script(
            "window.debugger = function(){};"
        )  # Disable debugger statements
        return driver
    except WebDriverException as e:
        print(f"Error initializing Selenium driver: {e}")
        return None
    
def login_uac(url=url, username=user, password=pwd):
    # 登录UAC，返回cookie
    cookie = None
    try:
        driver = init_driver(c_path, d_path)
        if not driver:
            return cookie
        driver.get(url+"login.php")
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "user_name"))
        )
        username_input = driver.find_element(By.ID, "user_name")  # 或 By.ID
        password_input = driver.find_element(By.ID, "password")
        login_button = driver.find_element(By.ID, "login")
        username_input.send_keys(username)
        password_input.send_keys(password)
        login_button.click()
        WebDriverWait(driver, 10).until(lambda d: d.title != "")
        if "RG-UAC" in driver.title:
            cookie_sessionid = driver.get_cookie("SEV_SESSID")
            if cookie_sessionid:
                cookie = cookie_sessionid["value"]
                driver.quit()
                return cookie
            else:
                print("登录失败，未获取到SEV_SESSID cookie")
                driver.quit()
                return None
        else:
            print("登录失败")
            driver.quit()
            return None
    except WebDriverException as e:
        print(f"Error logging in to {url}: {e}")
        driver.quit()
        return None

def query_user(name="", ip_addr="", mac_addr="", url=url):
    """适用于开发/测试环境，禁用SSL验证"""
    sessionid = login_uac(url, user, pwd)
    if not sessionid:
        print("登录UAC失败")
        return None
    url = f"{url}view/userAuthentication/organizedFrame/mainFunction/list.php"
    
    # 查询参数
    params = {
        "name": name,
        "ip_addr": ip_addr,
        "mac_addr": mac_addr  # 空值参数
    }
    
    # Cookie
    cookies = {
        "SEV_SESSID": sessionid
    }
    
    try:
        response = requests.post(
            url,
            params=params,
            cookies=cookies,
            verify=False,  # 禁用SSL证书验证
            timeout=30
        )
        
        if response.status_code == 200:
            html = response.text
            # 解析HTML
            soup = BeautifulSoup(html, "html.parser")
            # 查找表格
            form = soup.find("form", {"id": "form1"})
            tips = []
            if form:
                table = form.find_all("table", {"class": "list wtwo"})[-1]
                # 提取所有行
                rows = table.find_all("tr")
                for row in rows:
                    # 提取所有单元格
                    cells = row.find_all("td")
                    if cells:
                        tips.append([cell.get_text(strip=True) for cell in cells])
            else:
                print("未找到用户列表表格")
            return tips
        
        else:
            print(f"查询失败，状态码: {response.status_code}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None

def query_online_user(name="", ip_addr="", mac_addr="", url=url):
    """适用于开发/测试环境，禁用SSL验证"""
    sessionid = login_uac(url, user, pwd)
    if not sessionid:
        print("登录UAC失败")
        return None
    url = f"{url}view/realtimeMonitor/onlineip.php"
    # 查询参数
    params = {
        "user": name,
        "ip": ip_addr,
        "mac": mac_addr  # 空值参数
    }
    
    # Cookie
    cookies = {
        "SEV_SESSID": sessionid
    }
    
    try:
        response = requests.post(
            url,
            params=params,
            cookies=cookies,
            verify=False,  # 禁用SSL证书验证
            timeout=30
        )
        
        if response.status_code == 200:
            html = response.text
            # 解析HTML
            soup = BeautifulSoup(html, "html.parser")
            # 查找表格
            form = soup.find("form", {"id": "form1"})
            tips = []
            if form:
                # 提取所有行
                table = form.find_all("table", {"class": "list wtwo"})[-1]
                rows = table.find_all("tr")
                for row in rows:
                    # 提取所有单元格
                    cells = row.find_all("td")
                    if cells:
                        tips.append([cell.get_text(strip=True) for cell in cells])
            else:
                print("未找到用户列表表格")
            return tips
        
        else:
            print(f"查询失败，状态码: {response.status_code}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None

async def query_uac_async(record):
    contents = record.content.splitlines()
    name=""
    ip_addr=""
    mac_addr=""
    for content in contents:
        content = content.replace("：", ":")
        content = content.upper()
        if content.startswith("NAME"):
            name = content.split(":")[1]
        if content.startswith("IP"):
            ip_addr = content.split(":")[1]
        if content.startswith("MAC"):
            mac_addr = content.split(":")[1]
    tips = ""
    if "UAC" in contents[0]:
        tips = query_user(name, ip_addr, mac_addr)
    if "ONLINE" in contents[0]:
        tips = query_online_user(name, ip_addr, mac_addr)

    if tips:
        for i in tips:
            send_text(str(i), record.roomid)
    else:
        send_text("未查询到相关用户", record.roomid)

def get_token(url):
    sessionid = login_uac(url, user, pwd)
    if not sessionid:
        print("登录UAC失败")
        return None, None
    # 获取tokenid
    t_url = f"{url}view/userAuthentication/organizedFrame/mainFunction/list.php"
    params = {'parent_path': 'Root/教师办公'}
    cookies = {'SEV_SESSID': sessionid}
    response = requests.get(
        t_url,
        params=params,
        cookies=cookies,
        verify=False,  # 禁用SSL证书验证
        timeout=30
    )
    if response.status_code == 200:
        html = response.text
        # 解析HTML
        soup = BeautifulSoup(html, "html.parser")
        # 查找表格
        form = soup.find("form", {"id": "form1"})
        if form:
            tokenid = form.find("input", {"name": "tokenid"})["value"]
            if not tokenid:
                print("未找到tokenid")
                return None, sessionid
            else:
                return tokenid, sessionid
        else:
            print("未找到用户列表表格")
            return None, sessionid
    else:
        print(f"查询失败，状态码: {response.status_code}")
        return None, sessionid

def del_pc_user(pc_user, url=url):
    """适用于开发/测试环境，禁用SSL验证"""
    sessionid = login_uac(url, user, pwd)
    if not sessionid:
        print("登录UAC失败")
        return None
    url = f"{url}view/userAuthentication/organizedFrame/mainFunction/del_commit.php"
    user_encode = base64.b64encode(f"Root/教师办公/{pc_user}".encode("utf-8")).decode("utf-8")
    # 查询参数
    params = {
        "pagecur": "",
        "delCommit.x": "0",
        "delCommit.y": "0",
        "export_lan": "zh_CN",
        "name": "",
        "ip_addr": "",
        "mac_addr": "",
        "userStatus": "0",
        "moveList": "",
        "user[71]": user_encode,
        "left_group_path": "Root/教师办公",
        "rootpath": "Root"
    }
    # Cookie
    cookies = {
        "SEV_SESSID": sessionid
    }
    try:
        response = requests.post(
            url,
            params=params,
            cookies=cookies,
            verify=False,  # 禁用SSL证书验证
            timeout=30
        )
        
        if response.status_code == 200 and "alert(" not in response.text:
            return pc_user
        else:
            print(f"删除失败，状态码: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None

def add_pc_user(name, tel, ip_addr, url=url):
    """适用于开发/测试环境，禁用SSL验证"""
    tokenid, sessionid = get_token(url)
    if not tokenid:
        print("获取tokenid失败")
        return None
    
    url = f"{url}view/userAuthentication/organizedFrame/mainFunction/addUser_commit.php"
    params = {'parent_path': 'Root/教师办公'}
    # 查询参数
    form_data = {
        'tokenid': tokenid,
        'userName': f"PC{tel}",
        'show_userName': name,
        'description': '',
        'moveList': 'Root/教师办公',
        'phone': '',
        'email_addr': '',
        'userType': '1',
        'bind': '0',
        'bind_value': ip_addr,
        'hide_bind_value': '',
        'scanFrom1': '',
        'scanTo1': '',
        'scanFrom2': '',
        'scanTo2': '',
        'authMethod': '0',
        'pwd': '4rfv3edc',
        'repwd': '4rfv3edc',
        'num': '1',
        'overNum': '2',
        'effectTime': '0',
        'access_rule': '0',
        'http_proxy': '0',
        'userStatus': '0',
    }
    # Cookie
    cookies = {
        "SEV_SESSID": sessionid
    }
    try:
        response = requests.post(
            url,
            params=params,
            cookies=cookies,
            data=form_data,
            verify=False,  # 禁用SSL证书验证
            allow_redirects=True,
            timeout=30
        )
        
        if response.status_code == 200:
        # if response.status_code == 200 and "alert(" not in response.text:
            # print(response.text)
            return f"PC{tel}"
        else:
            print(f"添加失败，状态码: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None

async def del_pc_user_async(record):
    users = record.content.splitlines()
    for user in users[1:]:
        r = del_pc_user(user)
        if r:
            send_text(f"删除用户 {r} 成功", record.roomid)
        else:
            send_text(f"删除用户 {user} 失败", record.roomid)

async def add_pc_user_async(record):
    contents = record.content.upper().splitlines()
    name, tel, ip_addr = '', '', ''
    for content in contents[1:]:
        if "NAME" in content:
            name = content.split(":")[1].strip()
        if "TEL" in content:
            tel = content.split(":")[1].strip()
        if "IP" in content:
            ip_addr = content.split(":")[1].strip()
    
    if name or tel or ip_addr:
        r = add_pc_user(name, tel, ip_addr)
        if r:
            send_text(f"添加用户 {r} 成功", record.roomid)
        else:
            send_text(f"添加用户 {name} 失败", record.roomid)
    else:
        send_text("添加用户参数错误", record.roomid)

def export_pc_user(url=url):
    tokenid, sessionid = get_token(url)
    if not tokenid:
        print("获取tokenid失败")
        return None
    url = f"{url}view/userAuthentication/organizedFrame/mainFunction/export.php"
    query_string = {'lef_p': 'Root/教师办公'}
    cookies = {'SEV_SESSID': sessionid}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:145.0) Gecko/20100101 Firefox/145.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Referer': f'{url}view/userAuthentication/organizedFrame/mainFunction/list.php?left_path=Root%2F%E6%95%99%E5%B8%88%E5%8A%9E%E5%85%AC',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': url,
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'frame',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=4',
    }
    form_data = {
        'tokenid': tokenid,
        'pagecur': '',
        'save.x': '0',
        'save.y': '0',
        'export_lan': 'zh_CN',
        'name': '',
        'ip_addr': '',
        'mac_addr': '',
        'userStatus': '0',
        'moveList': '',
        'left_group_path': 'Root/教师办公',
        'rootpath': 'Root',
    }
    response = requests.post(
        url,
        params=query_string,
        cookies=cookies,
        headers=headers,
        data=form_data,
        verify=False,  # 禁用SSL证书验证
        stream=True
    )
    if response.status_code == 200:
        with open("pc_users.csv", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return "pc_users.csv"
    else:
        print(f"导出失败，状态码: {response.status_code}")
        return None

def get_one_ip():
    ip_list = []
    with open("pc_users.csv", "r", encoding="gbk") as f:
        lines = f.readlines()
        for line in lines[12:]:
            ips = line.split(",")[8]
            ip = ips.split(" ")[0]
            if ip:
                ip_4 = ip.split(".")[-1]
                ip_list.append(ip_4)
    print(ip_list)
    one_ip = ""
    for i in range(111, 200):
        if str(i) not in ip_list:
            one_ip = f"172.31.24.{i}"
            break
    return one_ip

async def get_one_ip_async(record):
    csv_file = export_pc_user()
    if csv_file:
        one_ip = get_one_ip()
        if one_ip:
            send_text(f"获取到的IP地址为: {one_ip}", record.roomid)
        else:
            send_text("获取IP地址失败", record.roomid)
