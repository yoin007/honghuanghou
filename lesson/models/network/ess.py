import requests
from base64 import b64decode, b64encode
from Crypto.Cipher import DES
from Crypto.Util.Padding import pad
from urllib.parse import quote
from config.config import Config
from bs4 import BeautifulSoup
from sendqueue import send_text

ess_conf = Config().get_config('ess', 'network.yaml')
root_url = ess_conf['url']
user = ess_conf['user']
pwd = ess_conf['pwd']
ess_url = root_url + "ess/"

headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": root_url,
        "Connection": "keep-alive",
        "Referer": ess_url,
        "Upgrade-Insecure-Requests": "1",
        "Priority": "u=0, i"
    }
def encrypt(content, key_base64='SphG5lQmUoU='):
    key = b64decode(key_base64)
    cipher = DES.new(key, DES.MODE_ECB)
    padded = pad(content.encode('utf-8'), DES.block_size)
    encrypted = cipher.encrypt(padded)
    return quote(b64encode(encrypted).decode('utf-8'))


def session():
    url = ess_url + "adminuserservlet"
    session = requests.Session()
    rsp = session.get(ess_url, headers=headers)
    cookie = rsp.headers['Set-Cookie'].split(';')[0]
    session.cookies.update({
        "JSESSIONID": cookie.split('=')[1],
        "smp": "true"
    })
    data = {
        "isCrypt": "true",
        "isXssFlag": "true",
        "kind": "login",
        "systemOperateTip": "+",
        "systemOperateFinishTip": "+",
        "newUrl": "",
        "managerId": user,
        "password": pwd
    }

    response = session.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return session
    else:
        return None

def add_user(tel, name):
    add_url = root_url + "ess/userservlet"
    ess_session = session()
    response = ess_session.get(add_url, headers=headers)
    if response.status_code != 200:
        return None
    tel = encrypt(tel)
    name = encrypt(name)
    raw_data = f"temp=&temp=&isCrypt=true&kind=add&pageType=&isGuideToHere=&shouldRefresh=&rename=true&scrollTop=&smpCurrentYear=&smpCurrentMonth=&smpCurrentDay=&smpCurrentHour=&smpCurrentMinute=&isInitAddPage=true&thirdpartyADEnable=false&existThirdparty=false&getThirdparty=false&secTempIndex=10007&isIpcEnable=false&currentPage=&sortColumnName=&sortOrder=&qy_userId=&qy_username=&qy_userGroupName=&qy_accurateQuery=false&qy_userType=&qy_userState=&queryType=&guestUserGroupName=%B7%C3%BF%CD%D3%C3%BB%A7%D7%E9&expireType_mayExpire=2&expireType_neverExpire=1&oldSelectedUserGroup=&nextPage=.%2Fuserservlet%3Fkind%3DaddPage%26noclearUserAccessInfo%3Dtrue&adqy_userId=&adqy_username=&adqy_userGroupName=&adqy_sex=&adqy_email=&adqy_certificateType=&adqy_certificateNo=&adqy_education=&adqy_telephone=&adqy_cellphone=&adqy_address=&adqy_postCode=&adqy_userIp=&adqy_userMac=&adqy_nasIp=&adqy_nasPort=&adqy_gatewayIp=&adqy_netmask=&adqy_mainDns=&adqy_wirelessSSID=&adqy_harddiskSerialNumber=&adqy_userClientType=&adqy_accurateQuery=&adqy_userType=&adqy_userState=&adqy_nickName=&userType=0&userState=NORMAL&userId={tel}&username={name}&nickName=&password=gsAHxTImdfPZNdLzJT3kYg%3D%3D&passwordConfirm=gsAHxTImdfPZNdLzJT3kYg%3D%3D&expiredType=1&userGroupName=6%D0%A3%C4%DAWiFi&secTemp=10007&secTempValue=%B7%C3%BF%CD%D3%C3%BB%A7%C4%A3%B0%E5&secTemp=2&sex=&email=2TXS8yU95GI%3D&certificateType=&education=&telephone=2TXS8yU95GI%3D&cellphone=2TXS8yU95GI%3D&address=2TXS8yU95GI%3D&postCode=2TXS8yU95GI%3D".strip()
    rsp = ess_session.post(add_url, headers=headers, data=raw_data)
    if rsp.status_code == 200 and "成功" in rsp.text:
        return True
    else:
        return None

def del_user(tel):
    del_url = root_url + "ess/userservlet"
    del_data = f"kind=delete&isFromUserGroup=false&enableSms=false&userIndex=&isInitUpadatePage=true&offlineMessageContent=&offline_patchServerSelecct=&offline_patchUrl=&offline_runAfterDownload=&privilege=&suspendType=&suspendedDate=&suspendedDateHour=&suspendedDateMinute=&reason=&clear=&currentPage=&sortColumnName=&sortOrder=&isGuideToHere=&shouldFocus=&qy_userId={tel}&qy_username=&qy_userType=&qy_userState=&qy_userGroupName=&qy_userGroupIndex=&qy_secTempName=&qy_accurateQuery=false&qy_createAdminId=&qy_isOnline=&qy_hasBlackList=&queryType=simple&adqy_userId=&adqy_username=&adqy_userType=&adqy_userState=&adqy_userGroupName=&adqy_secTempName=&adqy_sex=&adqy_email=&adqy_certificateType=&adqy_certificateNo=&adqy_education=&adqy_telephone=&adqy_cellphone=&adqy_address=&adqy_postCode=&adqy_accurateQuery=&adqy_isOnline=&adqy_nickName=&adqy_hasBlackList=&adqy_createAdminId=&adqy_accountActvateStatue=&adqy_useraccessType=&adqy_useraccessHarddiskNum=&adqy_useraccessIp=&adqy_useraccessMac=&adqy_useraccessImsi=&adqy_useraccessNasIp=&adqy_useraccessNasPort=&adqy_useraccessSsidName=&userId={tel}&username=&userGroupName=&secTempName=&createAdminId=&userType=&userState=&isOnline=&hasBlackList=&rowPerPage=300&jumpPage=1&checkbox={tel}&rowPerPage=300&jumpPage=1"
    ess_session = session()
    if not ess_session:
        return None
    response = ess_session.post(del_url, headers=headers, data=del_data)
    if response.status_code == 200 and "删除进度" in response.text:
        return True
    else:
        return None

def ess_online_user(tel='', name='', ip=''):
    online_url = root_url + "ess/onlineuserservlet"
    name = quote(name)
    data = f"kind=query&name=&userIndex=&operatorAll=false&isFromUserGroup=false&currentPage=&sortColumnName=&sortOrder=&qy_userId={tel}&qy_userName={name}&qy_userGroupName=&qy_userGroupIndex=&qy_secTempName=&qy_nasIp=&qy_userIp={ip}&qy_userIpv6=&qy_accurateQuery=false&queryType=simple&adqy_userId=&adqy_userName=&adqy_userGroupName=&adqy_secTempName=&adqy_authenMethod=&adqy_userIp=&adqy_userIpv6=&adqy_userMac=&adqy_harddiskSerialNumber=&adqy_nasIp=&adqy_nasPort=&adqy_imsi=&adqy_apMac=&adqy_ssid=&adqy_clientVersion=&adqy_hiResult=&adqy_start_loginday=&adqy_start_loginhour=&adqy_start_loginminute=&adqy_start_loginsecond=&adqy_end_loginday=&adqy_end_loginhour=&adqy_end_loginminute=&adqy_end_loginsecond=&adqy_startOnlineHour=&adqy_startOnlineMinute=&adqy_startOnlineSecond=&adqy_endOnlineHour=&adqy_endOnlineMinute=&adqy_endOnlineSecond=&adqy_nickName=&adqy_userType=&adqy_vlanId=&adqy_vlanName=&qy_terminalOsType=&adqy_accurateQuery=&userId={tel}&userName={name}&userGroupName=&secTempName=&terminalOsType=&userIp={ip}&userIpv6=&nasIp=&rowPerPage=200&jumpPage=1&rowPerPage=200&jumpPage=1"
    ess_session = session()
    if not ess_session:
        return None
    tips =[]
    response = ess_session.post(online_url, headers=headers, data=data)
    if response.status_code == 200:
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        main = soup.find('table', id='list')
        if main:
            try:
                rows = main.find_all('tr')
                for row in rows[1:]:
                    cells = row.find_all('td')
                    tips.append([cell.text.strip() for cell in cells[1:8]])
            except:
                pass

    return tips

def ess_mac(mac):
    mac_url = root_url + "ess/mobileterminalservlet"
    data = f"kind=query&qy_userId=&qy_mac={mac}&qy_isOnline=&qy_accurateQuery=false&startregisterTime=&endregisterTime=&currentPage=&sortColumnName=&sortOrder=&userId=&mac={mac}&isOnline=&startdate=&enddate=&rowPerPage=200&jumpPage=1&rowPerPage=200&jumpPage=1"
    ess_session = session()
    if not ess_session:
        return None
    tips =[]
    response = ess_session.post(mac_url, headers=headers, data=data)
    if response.status_code == 200:
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        main = soup.find('table', class_='main_list')
        if main:
            try:
                rows = main.find_all('tr')
                for row in rows[1:]:
                    cells = row.find_all('td')
                    tips.append([cell.text.strip() for cell in cells[1:8]])
            except:
                pass

    return tips

def query_user(tel='', name=''):
    url = root_url + "ess/userservlet"
    name = quote(name)
    data = f"kind=query&isFromUserGroup=false&enableSms=false&userIndex=&isInitUpadatePage=true&offlineMessageContent=&offline_patchServerSelecct=&offline_patchUrl=&offline_runAfterDownload=&privilege=&suspendType=&suspendedDate=&suspendedDateHour=&suspendedDateMinute=&reason=&clear=&currentPage=&sortColumnName=&sortOrder=&isGuideToHere=&shouldFocus=&qy_userId={tel}&qy_username={name}&qy_userType=&qy_userState=&qy_userGroupName=&qy_userGroupIndex=&qy_secTempName=&qy_accurateQuery=false&qy_createAdminId=&qy_isOnline=&qy_hasBlackList=&queryType=simple&adqy_nickName=&adqy_useraccessType=&adqy_useraccessHarddiskNum=&adqy_useraccessIp=&adqy_useraccessMac=&adqy_useraccessImsi=&adqy_useraccessNasIp=&adqy_useraccessNasPort=&adqy_useraccessSsidName=&userId={tel}&username={name}&userGroupName=&secTempName=&createAdminId=&userType=&userState=&isOnline=&hasBlackList=&rowPerPage=300&jumpPage=1&rowPerPage=300&jumpPage=1"
    ess_session = session()
    if not ess_session:
        return None
    tips =[]
    response = ess_session.post(url, headers=headers, data=data)
    if response.status_code == 200:
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        main = soup.find('table', id='list')
        if main:
            try:
                rows = main.find_all('tr')
                for row in rows[1:]:
                    cells = row.find_all('td')
                    tips.append([cell.text.strip() for cell in cells[1:7]])
            except:
                pass

    return tips

async def add_wifi_user(record):
    contents = record.content.upper().splitlines()
    tel = ''
    name = ''
    for content in contents:
        if "TEL:" in content:
            tel = content.split("TEL:")[1].strip()
        if "NAME:" in content:
            name = content.split("NAME:")[1].strip()
    rsp = add_user(tel, name)
    if rsp:
        send_text(f"{tel}添加成功", record.roomid)
    else:
        send_text(f"{tel}添加失败", record.roomid)

async def del_wifi_user(record):
    contents = record.content.upper().splitlines()
    tel = contents[-1].strip()
    rsp = del_user(tel)
    if rsp:
        send_text(f"{tel}删除成功", record.roomid)
    else:
        send_text(f"{tel}删除失败", record.roomid)

async def ess_online(record):
    contents = record.content.upper().splitlines()
    tel = ''
    name = ''
    ip = ''
    for content in contents:
        if "TEL:" in content:
            tel = content.split("TEL:")[1].strip()
        if "NAME:" in content:
            name = content.split("NAME:")[1].strip()
        if "IP:" in content:
            ip = content.split("IP:")[1].strip()
    tips = ess_online_user(tel=tel, name=name, ip=ip)
    if tips:
        for tip in tips:
            send_text(str(tip), record.roomid)
    else:
        send_text(f"查询失败", record.roomid)

async def ess_mac_async(record):
    contents = record.content.upper().splitlines()
    mac = None
    for content in contents:
        if "MAC:" in content:
            mac = content.split("MAC:")[1].strip().replace(":", "").replace("-", "").replace(".", "")
    if not mac:
        send_text(f"查询失败", record.roomid)
        return
    tips = ess_mac(mac)
    if tips:
        for tip in tips:
            send_text(str(tip), record.roomid)
    else:
        send_text(f"查询失败", record.roomid)

async def ess_user(record):
    contents = record.content.upper().splitlines()
    tel = ''
    name = ''
    for content in contents:
        if "TEL:" in content:
            tel = content.split("TEL:")[1].strip()
        if "NAME:" in content:
            name = content.split("NAME:")[1].strip()
    tips = query_user(tel=tel, name=name)
    if tips:
        for tip in tips:
            send_text(str(tip), record.roomid)
    else:
        send_text(f"查询失败", record.roomid)

def black_user(tel=''):
    url = root_url + "ess/blacklistservlet"
    data = f"kind=addBlacklist&qy_userId=&qy_userIp=&qy_userMac=&qy_nasIp=&qy_nasPort=&qy_isOpen=&sortColumnName=&sortOrder=&currentPage=&qy_isExpired=&qy_ssidName=&qy_wirelessApMac=&isMustInputUserId=false&serverTime=&blackListIsFromUser=false&doRefreshOpener=&userId={tel}&harddiskSerialNumber=&userIp=&userMac=&nasIp=&nasPort=&ssidName=&wirelessApMac=&validType=2&validDateYear=&validDateMonth=&validDateDay=&validDateHour=&validDate_YMD=&validDate_hour=&validDate_minute=&validDate_second=&validDate=&isOpen=Y&promptInfo=%C4%FA%D2%D1%B1%BB%BD%FB%D6%B9%CA%B9%D3%C3%CD%F8%C2%E7%21&descInfo="
    ess_session = session()
    if not ess_session:
        return None
    headers.update({
        "Content-Type": "application/x-www-form-urlencoded;",
    })
    response = ess_session.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return True
    else:
        return False

def del_black_user(tel=''):
    ess_session = session()
    if not ess_session:
        return None
    black_url = root_url + "ess/blacklistservlet?kind=query"
    resp = ess_session.get(black_url)
    if resp.status_code != 200:
        return None
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    main = soup.find('table', class_='main_list')
    check_value = ''
    if not main:
        return None
    try:
        rows = main.find_all('tr')
        for row in rows[1:]:
            cells = row.find_all('td')
            user = cells[1].text.strip()
            if tel == user:
                check_value = cells[0].find('input')['value']
                break
    except:
        return None
    if check_value == '':
        return None
    url = root_url + "ess/blacklistservlet"
    data = f"kind=delete&currentPage=&sortColumnName=&sortOrder=&blacklistIndex=&qy_promptInfo=&qy_userId=&qy_userIp=&qy_userMac=&qy_nasIp=&qy_nasPort=&qy_isOpen=&qy_isExpired=&qy_ssidName=&qy_wirelessApMac=&qy_accurateQuery=false&blackListIsFromUser=false&doRefreshOpener=&userId=&userIp=&userMac=&isExpired=&nasIp=&nasPort=&isOpen=&promptInfo=&ssidName=&wirelessApMac=&rowPerPage=20&jumpPage=1&checkbox={check_value}&rowPerPage=20&jumpPage=1"
    headers.update({
        "Content-Type": "application/x-www-form-urlencoded;",
    })  
    response = ess_session.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return True
    else:
        return False

async def black_user_async(record):
    contents = record.content.upper().splitlines()
    for content in contents[1:]:
        tel = content.strip()
        if tel:
            black_user(tel)
            send_text(f"{tel} 已添加到黑名单", record.roomid)

async def del_black_user_async(record):
    contents = record.content.upper().splitlines()
    for content in contents[1:]:
        tel = content.strip()
        if tel:
            del_black_user(tel)
            send_text(f"{tel} 已从黑名单中删除", record.roomid)
