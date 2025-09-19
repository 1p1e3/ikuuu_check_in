import os
import requests
import json
import sys
import base64
import re


# ikuuu 最新可用地址
HOST = "https://ikuuu.de"

# 登录接口
LOGIN_URL = f"{HOST}/auth/login"

# 必要的请求 header，过检测
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
}

# 签到接口
CHECK_IN_URL = f"{HOST}/user/checkin"

# 首页地址
HOME_URL = f"{HOST}/user"


# 飞书机器人 Key
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/"
FEISHU_KEY = ""



def get_account():
    """读取青龙面板中配置的ikuuu账号和密码"""
    emails = os.getenv("IKUUU_EMAIL")
    pwds = os.getenv("IKUUU_PWD")

    if not emails or not pwds:
        print("🚨 没有检查到邮箱和密码，请确认是否已配置")
        sys.exit(0)
    
    email_list = emails.split("\n")
    pwd_list = pwds.split("\n")


    if len(email_list) != len(pwd_list):
        print("🚨 邮箱和密码数量不一致，请检查")
        sys.exit(0)

    print(f"🟢 读取到 {len(email_list)} 个账号")

    account_list = []

    for i in range(len(email_list)):
        account = {}
        account["email"] = email_list[i]
        account["passwd"] = pwd_list[i]
        account_list.append(account)

    return account_list




def login(account: dict):
    """登录"""
    res = requests.post(url=LOGIN_URL, headers=HEADERS, data=account)


    res_dict = json.loads(res.content)

    if res_dict["ret"] == 0:
        print(f"🔴 账号: {account['email']} 登录失败, 原因: {res_dict['msg']}")
        return None
    
    print(f"🟢 账号: {account['email']} 登录成功")

    return res.cookies



def check_in(cookies):
    """签到"""
    res = requests.post(url=CHECK_IN_URL, headers=HEADERS, cookies=cookies)
    
    res_dict = json.loads(res.content)

    return res_dict


def decode_base64(cookies):
    """对user页(首页)进行base64解码, 获取原始html元素"""
    res = requests.get(url=HOME_URL, headers=HEADERS, cookies=cookies)

    originBody_match = re.search(r'var originBody = "(.*?)"', res.text)

    originBody = ""

    if originBody_match:
        originBody = originBody_match.group(1)
    else:
        print("🔴 没有找到首页的原始 html 元素")

    # 解码 Base64 字符串
    decoded_bytes = base64.b64decode(originBody)
    decoded_str = decoded_bytes.decode('utf-8')  # 转换为字符串

    return decoded_str


def get_rest(decoded_html_str: str):
    """从解码后的元素html元素字符串中找到剩余流量"""
    counter_match = re.search(r'<span class="counter">(.*?)</span> GB', decoded_html_str)
    if counter_match:
        return counter_match.group(1)
    return "🔴 没有查询到剩余流量"

    

def send_notify(notify_msg):
    """发送飞书通知"""
    webhook = f"{FEISHU_WEBHOOK}{FEISHU_KEY}"

    msg = {
        "msg_type": "text",
        "content": {
            "text": notify_msg
        }
    }

    r = requests.post(url=webhook, json=msg)

    if r.json()["msg"] == "success":
        print("🟢 飞书消息发送成功")


def main():
    notify_msg = ""

    success_list = []
    fail_list = []

    # 读取账号
    account_list = get_account()

    for i in account_list:
        # 登录
        cookies = login(i)
        if not cookies:
            fail_list.append(i['email'])
            continue
        
        # 签到
        check_in_res = check_in(cookies)
        
        notify_msg += f"🤖 账号 {i['email']}\n"
        notify_msg += f"🕐 签到结果: {check_in_res['msg']}\n"

        # 查询剩余流量
        decoded_str = decode_base64(cookies)
        notify_msg += f"🔢 剩余流量: {get_rest(decoded_str)} GB\n"
        notify_msg += "-----------------------------------\n\n\n"

        success_list.append(i['email'])

    
    notify_msg += f"🔶 读取到的账号总数: {len(account_list)}\n\n"
    notify_msg += f"✅ 成功走完流程的账号(已签到也视为成功): {success_list}\n, 数量: {len(success_list)}\n\n"
    notify_msg += f"❌ 没有走完流程的账号(登录失败或其他原因): {fail_list}\n, 数量: {len(fail_list)}\n"


    send_notify(notify_msg)


if __name__ == "__main__":
    main()