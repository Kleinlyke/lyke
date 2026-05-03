# ikuuu 自动签到
# 优化版本 - 支持自动域名检测、获取剩余流量和今日已用流量

import time
import random
import requests
import re
import base64
import json
import urllib.parse
import os
from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings()

# ==================== 配置区域 ====================
USER_EMAIL = os.getenv("IKUUU_EMAIL")
USER_PASSWORD = os.getenv("IKUUU_PASSWORD")
PUSHDEER_KEY = os.getenv("PUSHDEER_KEY")
# 可以添加检查，如果环境变量未设置则抛出错误
if not all([USER_EMAIL, USER_PASSWORD]):
    raise ValueError("Missing required environment variables: IKUUU_EMAIL, IKUUU_PASSWORD")
# =================================================

# 初始域名和备用域名
IKUUU_HOST = "ikuuu.nl"
BACKUP_HOSTS = ["ikuuu.de","ikuuu.one", "ikuuu.pw", "ikuuu.me", "ikuuu.club", "ikuuu.vip", "ikuuu.fyi","ikuuu.win"]
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class DomainManager:
    """域名管理器，自动检测可用域名"""
    
    def __init__(self):
        self.current_host = IKUUU_HOST
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
    
    def test_host_reachable(self, host):
        """测试域名是否可达"""
        try:
            print(f"🔍 测试域名: {host}")
            response = self.session.get(
                f"https://{host}/",
                timeout=10,
                allow_redirects=True,
                verify=False
            )
            if response.status_code == 200:
                print(f"✅ 域名 {host} 可用")
                return True
            else:
                print(f"⚠️ 域名 {host} 返回状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 域名 {host} 不可用: {e}")
            return False
    
    def extract_domains_from_content(self, content):
        """从网页内容中提取可用域名"""
        domains = []
        patterns = [
            r'https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/auth/login',
            r'(ikuuu\.[a-zA-Z0-9.-]+)',
            r'新域名[:：]\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'域名[:：]\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                domain = match.strip().lower()
                if (domain and '.' in domain and 
                    len(domain) > 3 and len(domain) < 50):
                    domains.append(domain)
        
        return list(set(domains))
    
    def get_available_domains_from_page(self, host):
        """从页面获取新域名信息"""
        try:
            response = self.session.get(
                f"https://{host}/",
                timeout=10,
                allow_redirects=True,
                verify=False
            )
            
            if response.status_code == 200:
                # 检查是否有域名变更信息
                change_indicators = [
                    '官网域名已更改', 'Domain deprecated', '域名已更新', 
                    '新域名', '最新域名', '域名变更', '网站已迁移'
                ]
                
                if any(indicator in response.text for indicator in change_indicators):
                    print(f"🔄 检测到域名变更通知: {host}")
                    domains = self.extract_domains_from_content(response.text)
                    return domains
                else:
                    # 即使没有变更通知，也尝试提取域名
                    domains = self.extract_domains_from_content(response.text)
                    return [d for d in domains if 'ikuuu' in d]
        except Exception as e:
            print(f"⚠️ 获取页面信息失败 {host}: {e}")
        
        return []
    
    def find_working_domain(self):
        """寻找可用的域名"""
        print(f"🏠 当前域名: {self.current_host}")
        
        # 1. 测试当前域名
        if self.test_host_reachable(self.current_host):
            return self.current_host
        
        # 2. 从当前域名页面获取新域名
        discovered_domains = self.get_available_domains_from_page(self.current_host)
        print(f"🔍 发现的新域名: {discovered_domains}")
        
        # 3. 测试发现的域名
        for domain in discovered_domains:
            if domain != self.current_host and self.test_host_reachable(domain):
                print(f"🎉 找到可用域名: {domain}")
                self.current_host = domain
                return domain
        
        # 4. 测试备用域名
        print("🔄 测试备用域名列表...")
        for host in BACKUP_HOSTS:
            if host != self.current_host and self.test_host_reachable(host):
                print(f"🎉 备用域名可用: {host}")
                self.current_host = host
                return host
        
        # 5. 都不可用，尝试直接访问原始域名
        print("⚠️ 所有域名测试失败，尝试使用原始域名")
        return self.current_host

class ikuuu():
    def __init__(self, email, password):
        self.msg = ''
        self.email = email.strip()
        self.passwd = password.strip()
        self.username = self.email
        self.session = requests.Session()
        
        # 域名管理器
        self.domain_manager = DomainManager()
        self.base_host = self.domain_manager.find_working_domain()
        
        # 更新请求头
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': f'https://{self.base_host}/auth/login',
            'Origin': f'https://{self.base_host}',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive'
        })
        
    def login(self, retry=3):
        login_url = f'https://{self.base_host}/auth/login'
        time.sleep(random.uniform(1, 3))
        
        data = {
            'email': self.email,
            'passwd': self.passwd,
            'remember_me': 'on'  
        }
        
        for i in range(retry):
            try:
                # 先获取登录页面
                self.session.get(login_url, timeout=15, verify=False)
                
                # 提交登录表单
                res = self.session.post(
                    login_url,
                    data=data,
                    timeout=15,
                    allow_redirects=False,
                    verify=False
                )
                
                # 检查登录是否成功（重定向到用户页面）
                if res.status_code == 302 and ('user' in res.headers.get('Location', '') or 'login' not in res.headers.get('Location', '')):
                    print(f"✅ 登录成功: {self.email}")
                    return True
                elif i < retry-1:
                    print(f"⚠️ 第{i+1}次登录失败，{self.email}，重试中...")
                    time.sleep(random.uniform(2, 4))
            except Exception as e:
                if i < retry-1:
                    print(f"⚠️ 第{i+1}次登录异常 {self.email}：{str(e)}，重试中...")
                    time.sleep(random.uniform(2, 4))
        
        print(f"❌ 登录失败: {self.email}")
        return False
    
    def get_traffic_info(self, html_content):
        """从页面提取流量信息（剩余流量和今日已用流量）"""
        traffic_info = {
            'remaining': '未知',
            'used_today': '0B',
            'total': '未知'
        }

        def extract_from_soup(soup):
            """从BeautifulSoup对象中提取卡片中的流量信息"""
            # 查找所有card-wrap（流量卡片）
            card_wraps = soup.find_all('div', class_='card-wrap')
            for card in card_wraps:
                # 获取卡片标题
                header = card.find('div', class_='card-header')
                if not header:
                    continue
                h4 = header.find('h4')
                if not h4:
                    continue
                title = h4.get_text(strip=True)

                # 提取剩余流量
                if '剩余流量' in title:
                    body = card.find('div', class_='card-body')
                    if body:
                        counter = body.find('span', class_='counter')
                        if counter:
                            value = counter.get_text(strip=True)
                            # 单位可能在counter后面
                            unit = counter.next_sibling
                            unit = unit.strip() if unit and isinstance(unit, str) else ''
                            traffic_info['remaining'] = f"{value}{unit}"

                # 提取今日已用
                stats = card.find('div', class_='card-stats')
                if stats:
                    stats_title = stats.find('div', class_='card-stats-title')
                    if stats_title:
                        # 尝试直接找li中的文本
                        li = stats_title.find('li', class_='breadcrumb-item active')
                        if li:
                            text = li.get_text(strip=True)
                            if '今日已用' in text:
                                # 提取数值和单位
                                parts = text.split('：')[-1].split(':')[-1].strip()
                                traffic_info['used_today'] = parts
                        else:
                            # 如果没有li，直接从stats_title取文本
                            text = stats_title.get_text(strip=True)
                            if '今日已用' in text:
                                parts = text.split('：')[-1].split(':')[-1].strip()
                                traffic_info['used_today'] = parts

        try:
            # 方法1: 尝试Base64解码
            base64_match = re.search(r'var originBody = "([^"]+)"', html_content)
            if base64_match:
                try:
                    base64_content = base64_match.group(1)
                    decoded = base64.b64decode(base64_content).decode('utf-8')
                    soup_decoded = BeautifulSoup(decoded, 'html.parser')
                    extract_from_soup(soup_decoded)
                except Exception as e:
                    print(f"Base64解码失败: {e}")

            # 如果解码后未找到所需信息，再从原始HTML中提取
            if traffic_info['remaining'] == '未知' or traffic_info['used_today'] == '0B':
                soup_orig = BeautifulSoup(html_content, 'html.parser')
                extract_from_soup(soup_orig)

            # 方法2: 正则提取今日已用（作为后备）
            if traffic_info['used_today'] == '0B':
                used_match = re.search(r'今日已用[:：]\s*([\d.]+)\s*([KMGTP]?B)', html_content, re.IGNORECASE)
                if used_match:
                    traffic_info['used_today'] = used_match.group(1) + used_match.group(2)

            # 提取总流量（可选）
            total_match = re.search(r'([\d.]+\s*GB)\s*/\s*([\d.]+\s*GB)', html_content)
            if total_match:
                traffic_info['total'] = total_match.group(2)
            else:
                total_match2 = re.search(r'总计[:：]\s*([\d.]+\s*[KMGTP]?B)', html_content, re.IGNORECASE)
                if total_match2:
                    traffic_info['total'] = total_match2.group(1)

        except Exception as e:
            print(f"提取流量信息失败：{str(e)}")

        return traffic_info
    
    def get_user_info(self):
        """获取用户信息（用户名和流量）"""
        user_url = f'https://{self.base_host}/user'
        
        try:
            time.sleep(random.uniform(1, 2))
            user_res = self.session.get(user_url, timeout=15, verify=False)
            user_res.raise_for_status()
            
            # 解析用户名
            soup = BeautifulSoup(user_res.text, 'html.parser')
            # 优先查找包含用户名的div
            name_div = soup.find('div', class_='d-sm-none d-lg-inline-block')
            if name_div:
                name_text = name_div.get_text(strip=True)
                # 去除 "Hi, " 前缀
                if name_text.startswith('Hi,'):
                    self.username = name_text.replace('Hi,', '').strip()
                else:
                    self.username = name_text
                print(f"✅ 成功获取用户名：{self.username}")
            else:
                # 备选：查找navbar-brand
                name_elem = soup.find('span', class_='navbar-brand')
                if name_elem:
                    self.username = name_elem.text.strip()
                    print(f"✅ 成功获取用户名（备选）：{self.username}")
                else:
                    print("⚠️ 未找到用户名标签，使用邮箱作为用户名")
                    self.username = self.email
            
            # 获取流量信息
            traffic_info = self.get_traffic_info(user_res.text)
            
            return True, traffic_info, user_res.text
            
        except Exception as e:
            print(f"获取用户信息失败：{str(e)}")
            return False, {'remaining': '未知', 'used_today': '0B', 'total': '未知'}, ''
    
    def sign(self):
        print(f"🌐 使用域名: {self.base_host}")
        print(f"👤 账号: {self.email}")
        
        if not self.login():
            self.msg = f"[登录]：{self.email} 登录失败（风控/网络/账号密码），请检查\n\n"
            print(self.msg)
            return self.msg
        
        # 执行签到
        sign_url = f'https://{self.base_host}/user/checkin'
        sign_result = ""
        try:
            time.sleep(random.uniform(1, 2))
            sign_res = self.session.post(sign_url, timeout=15, verify=False)
            sign_res.raise_for_status()
            # 解析签到结果
            try:
                sign_json = sign_res.json()
                if "已经签到" in sign_json.get('msg', ''):
                    sign_result = f"已经签到过了"
                elif "获得" in sign_json.get('msg', ''):
                    sign_result = sign_json['msg']
                else:
                    sign_result = f"未知结果: {sign_json.get('msg', '无信息')}"
            except:
                sign_result = "响应解析失败"
        except Exception as e:
            sign_result = f"请求失败 {str(e)}"
        
        # 获取用户信息和流量（签到后的最新信息）
        success, traffic_info, _ = self.get_user_info()
        
        if not success:
            # 如果获取用户信息失败，但签到可能成功，使用默认值
            traffic_info = {'remaining': '未知', 'used_today': '未知', 'total': '未知'}
        
        # 构建完整的消息（使用Markdown换行：两个空格+换行）
        self.msg = f"[登录账号]：{self.username}  \n"
        self.msg += f"[签到状态]：{sign_result}  \n"
        self.msg += f"[剩余流量]：{traffic_info['remaining']}  \n"
        self.msg += f"[今日已用]：{traffic_info['used_today']}  \n"
        if traffic_info['total'] != '未知':
            self.msg += f"[总流量]：{traffic_info['total']}  \n"
        self.msg += f"[当前域名]：{self.base_host}\n"
        
        print(self.msg)
        return self.msg
    
    def get_sign_msg(self):
        return self.sign()


def pushdeer_send(title, desp):
    """使用PushDeer发送通知"""
    if not PUSHDEER_KEY:
        print("❌ 未配置PushDeer密钥，跳过推送")
        return False
        
    try:
        url = "https://api2.pushdeer.com/message/push"
        data = {
            'pushkey': PUSHDEER_KEY,
            'text': title,
            'desp': desp,  # 直接使用已处理好格式的desp
            'type': 'markdown'
        }
        response = requests.post(url, data=data, timeout=10)
        result = response.json()
        if result.get('code') == 0:
            print("✅ PushDeer推送成功")
            return True
        else:
            print(f"❌ PushDeer推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ PushDeer推送异常: {str(e)}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 开始ikuuu签到")
    print("=" * 50)
    
    # 创建实例并执行签到
    run = ikuuu(USER_EMAIL, USER_PASSWORD)
    msg = run.get_sign_msg()
    
    print("=" * 50)
    print("📊 签到结果：")
    print(msg)
    print("=" * 50)
    
    # 发送PushDeer通知
    if PUSHDEER_KEY:
        pushdeer_send("ikuuu签到通知", msg)
    else:
        print("❌ 未配置PushDeer密钥，跳过推送")
    
    print("✅ 签到完成")
