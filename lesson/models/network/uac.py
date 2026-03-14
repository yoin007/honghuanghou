import requests
import os
import re, urllib3
from bs4 import BeautifulSoup
import json
from base64 import b64encode
from Crypto.Cipher import AES
import shutil

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from models.network.ess import query_user as ess_query_user
from models.network.ess import black_user
from config.config import Config
from sendqueue import send_text

uac_conf = Config().get_config("uac", "network.yaml")
url = uac_conf["url"]
user = uac_conf["user"]
pwd = uac_conf["pwd"]
admin = Config().get_config("admin", "wechat.yaml")

def get_token(url=url):
    url = url + "/login.php"
    resp = requests.get(url, verify=False)
    cookies = resp.cookies.get_dict().get("SEV_SESSID", "")
    html = resp.text
    hex_str  = re.search(r"document\.write\((.*)\)", html).group(1).split("'")[1]
    key_list = re.search(r'var key = \[([\d,\s]+)\]', html).group(1)
    key_list = [int(x) for x in key_list.split(',')]

    # 2. 把 JS 算法翻译成 Python
    def jmy_decrypt(hex_string, key):
        out = []
        for i in range(0, len(hex_string), 2):
            b = int(hex_string[i:i+2], 16)          # 取一个字节
            k = key[(i//2) % len(key)]              # 对应 key
            out.append(b ^ k)                       # 异或
        return bytes(out).decode('utf-8', errors='ignore')

    html = jmy_decrypt(hex_str, key_list)
    soup = BeautifulSoup(html, 'html.parser')
    token = soup.find('input', {'id': 'token'}).get('value')
    return token, cookies

def crypto_encrypt(data, okey) -> str:
    # 1. JSON 序列化（紧凑格式）
    text = json.dumps(data, separators=(',', ':'))

    # 2. 再做一次 Base64 编码（与 JS 侧保持一致）
    text_b64 = b64encode(text.encode('utf-8')).decode('ascii')

    # 3. 处理 key：16 字节，不足补 \0，超出截断
    key = okey.encode('utf-8')
    key = (key[:16] if len(key) >= 16 else key.ljust(16, b'\0'))

    # 4. 固定 IV
    iv = b'1234567887654321'

    # 5. ZeroPadding：明文长度必须是 16 的倍数
    data_bytes = text_b64.encode('utf-8')
    if len(data_bytes) % AES.block_size != 0:
        # ZeroPadding：后面补 0x00
        pad_len = AES.block_size - (len(data_bytes) % AES.block_size)
        data_bytes += b'\0' * pad_len

    # 6. AES-256-CBC 加密
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(data_bytes)

    # 7. 最后再做一次 Base64 编码并返回字符串
    return b64encode(b64encode(encrypted)).decode('latin1')

def login_uac(username=user, password=pwd, url=url):
    token, cookies = get_token(url)
    headers ={
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": f"SEV_SESSID={cookies}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    }
    login_url = url + "login_commit.php"
    en_pwd = crypto_encrypt(password, token[:16])
    data = f"tokenid=&token={token}&encrypt=1&lang=zh_CN&name={username}&password={en_pwd}"
    session = requests.Session()
    resp = session.post(login_url, headers=headers, data=data, verify=False)
    if "index.php" in resp.text:
        new_cookies = resp.headers.get('Set-Cookie').split(";")[0]
        return new_cookies
    else:
        return None

def get_tokenid(url, cookies):
    headers = {
        "Cookie": cookies,
    }
    resp = requests.get(url, verify=False, headers=headers)
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")
    tokenid = soup.find("input", {"name": "tokenid"}).get("value")
    return tokenid

def query_user(name="", ip_addr="", mac_addr="", url=url):
    """适用于开发/测试环境，禁用SSL验证"""
    sessionid = login_uac()
    if not sessionid:
        print("登录UAC失败")
        return None
    headers = {"Cookie": sessionid}
    url = f"{url}view/userAuthentication/organizedFrame/mainFunction/list.php"
    
    # 查询参数
    params = {
        "name": name,
        "ip_addr": ip_addr,
        "mac_addr": mac_addr  # 空值参数
    } 
    
    try:
        response = requests.post(
            url,
            params=params,
            headers=headers,
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
    sessionid = login_uac()
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
    headers = {"Cookie": sessionid}
    try:
        response = requests.post(
            url,
            params=params,
            headers=headers,
            verify=False,  # 禁用SSL证书验证
            timeout=30
        )
        
        if response.status_code == 200:
            print(html)
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

def del_pc_user(pc_user, url=url):
    """适用于开发/测试环境，禁用SSL验证"""
    sessionid = login_uac()
    if not sessionid:
        print("登录UAC失败")
        return None
    url = f"{url}view/userAuthentication/organizedFrame/mainFunction/del_commit.php"
    user_encode = b64encode(f"Root/教师办公/{pc_user}".encode("utf-8")).decode("utf-8")
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
    headers = {"Cookie": sessionid}
    try:
        response = requests.post(
            url,
            params=params,
            headers=headers,
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
    sessionid = login_uac()
    if not sessionid:
        print("登录UAC失败")
        return None
    add_url = f"{url}/view/userAuthentication/organizedFrame/mainFunction/addUser.php"
    tokenid = get_tokenid(add_url, sessionid)
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
    headers = {"Cookie": sessionid}
    try:
        response = requests.post(
            url,
            params=params,
            headers=headers,
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
    sessionid = login_uac()
    if not sessionid:
        print("登录UAC失败")
        return None
    add_url = f"{url}/view/userAuthentication/organizedFrame/mainFunction/addUser.php"
    tokenid = get_tokenid(add_url, sessionid)
    if not tokenid:
        print("获取tokenid失败")
        return None
    url = f"{url}view/userAuthentication/organizedFrame/mainFunction/export.php"
    query_string = {'lef_p': 'Root/教师办公'}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:145.0) Gecko/20100101 Firefox/145.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Referer': f'{url}view/userAuthentication/organizedFrame/mainFunction/list.php?left_path=Root%2F%E6%95%99%E5%B8%88%E5%8A%9E%E5%85%AC',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': url,
        'Cookie': sessionid,
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

def init_white():
    if os.path.exists("white_list.txt"):
        os.remove("white_list.txt")
    shutil.copy("white_list_template.txt", "white_list.txt")
    
def black_ip(ip_addr="", init=False):
    sessionid = login_uac()
    if not sessionid:
        print("登录UAC失败")
        return None
    add_url = f"{url}/view/userAuthentication/organizedFrame/mainFunction/addUser.php"
    tokenid = get_tokenid(add_url, sessionid)
    if not tokenid:
        print("获取tokenid失败")
        return None
    black_url = f"{url}view/systemObject/addressBook/edit.php?name=黑名单&pagecur=1&pagesize=20&template="
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:145.0) Gecko/20100101 Firefox/145.0',
        'Cookie': sessionid,
    }
    resp = requests.get(black_url, headers=headers, verify=False)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        ips = soup.find("textarea", id="ip").text
        ips = ips + f"\r\n{ip_addr}"
        if init:
            ips = "9.8.7.6"
            init_white()
        data = f"tokenid={tokenid}&pagecur=1&pagesize=20&ip={ips}&name=黑名单"
        black_url = f"{url}view/systemObject/addressBook/commit.php"
        params = {"action": "edit"}
        headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        resp = requests.post(black_url, headers=headers, data=data, verify=False, params=params)
        if resp.status_code == 200:
            # print(resp.text)
            return ip_addr
        else:
            print(f"添加IP {ip_addr} 到黑名单失败，状态码: {resp.status_code}")
            return None

async def black_ip_async(record):
    ip_addr = record.content.splitlines()[-1].strip()
    if ip_addr:
        ip = black_ip(ip_addr)
        if ip:
            send_text(f"IP地址 {ip_addr} 已添加到黑名单", record.roomid)
        else:
            send_text(f"添加IP地址 {ip_addr} 到黑名单失败", record.roomid)
    else:
        send_text(f"添加IP地址 {ip_addr} 到黑名单失败，IP地址为空", record.roomid)

def del_black_ip(ip_addr):
    sessionid = login_uac()
    if not sessionid:
        print("登录UAC失败")
        return None
    add_url = f"{url}/view/userAuthentication/organizedFrame/mainFunction/addUser.php"
    tokenid = get_tokenid(add_url, sessionid)
    if not tokenid:
        print("获取tokenid失败")
        return None
    black_url = f"{url}view/systemObject/addressBook/edit.php?name=黑名单&pagecur=1&pagesize=20&template="
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:145.0) Gecko/20100101 Firefox/145.0',
        'Cookie': sessionid,
    }
    resp = requests.get(black_url, headers=headers, verify=False)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        ips = soup.find("textarea", id="ip").text
        if ip_addr not in ips:
            return None
        if ips.startswith(ip_addr):
            ips = ips.replace(f"{ip_addr}\r\n", "")
        else:
            ips = ips.replace(f"\r\n{ip_addr}", "")
        data = f"tokenid={tokenid}&pagecur=1&pagesize=20&ip={ips}&name=黑名单"
        black_url = f"{url}view/systemObject/addressBook/commit.php"
        params = {"action": "edit"}
        headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        resp = requests.post(black_url, headers=headers, data=data, verify=False, params=params)
        if resp.status_code == 200:
            # print(resp.text)
            return ip_addr
        else:
            print(f"删除IP {ip_addr} 从黑名单失败，状态码: {resp.status_code}")
            return None

async def del_black_ip_async(record):
    ip_addr = record.content.splitlines()[-1].strip()
    if ip_addr:
        ip = del_black_ip(ip_addr)
        if ip:
            send_text(f"IP地址 {ip_addr} 已从黑名单中删除", record.roomid)
        else:
            send_text(f"删除IP地址 {ip_addr} 从黑名单失败", record.roomid)
    else:
        send_text(f"删除IP地址 {ip_addr} 从黑名单失败，IP地址为空", record.roomid)

def high_risk_data(count=8, ic=1, fc=50, url=url):
    sessionid = login_uac()
    if not sessionid:
        print("登录UAC失败")
        return None
    url = url[:-1]+ ':9091'
    hr_url = f'{url}/da/2/get_ajax_highrisk.php?order=DESC&type=flow'
    params = {"order": "DESC", "type": "flow"}
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Origin': url,
        'Referer': f'{url}/da/2/main.php',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }
    cookies = {"SEV_SESSID": "8916ede6b8a11177473253c2fd17a6aa"}
    users = []
    # 发送 POST（无 body，仅 headers 与 cookies）
    resp = requests.post(hr_url, headers=headers, cookies=cookies, params=params, verify=False)   # 等价于 curl 的 --insecure
    if resp.status_code == 200:
        data = resp.json()
        if data:
            for d in data[:30]:
                if int(d['count']) >= count*1024*1024*1024 or int(d['fcount'])>fc or int(d['icount'])>=ic:
                    users.append(d)
        return users
    else:
        print(f"获取高风险IP失败，状态码: {resp.status_code}")
        return None

def high_risk():
    datas = high_risk_data()
    if datas:
        if not os.path.exists("white_list.txt"):
            init_white()
        with open("white_list.txt", "r") as f:
            white_ips = f.readlines()
            white_ips = [ip.strip() for ip in white_ips]
        for data in datas:
            user = data['user']
            user_data = query_user(name=user)
            if user_data:
                ip_data=user_data[0][4]
                user_name = user_data[0][2]
                if ip_data:
                    ips = ip_data.split(' ')
                    for ip in ips:
                        if ip != "……":
                            if ip in white_ips:
                                continue
                            else:
                                black_ip(ip)
                                # send_text=print
                                send_text(f"{user_name} 的IP地址 {ip} 已添加到黑名单", admin)
                else:
                    user_data = ess_query_user(tel=user)
                    if user_data:
                        user_name = user_data[0][1]
                        if user in white_ips:
                            continue
                        else:
                            black_user(user)
                            # send_text=print
                            send_text(f"{user_name} 的手机号 {user} 已添加到黑名单", admin)