import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import threading
import time
from flask import Flask, Response, render_template_string, request, redirect, url_for
import xml.sax.saxutils as saxutils
import re
from urllib.parse import quote, unquote
from functools import wraps
from base64 import b64decode

app = Flask(__name__)

CONFIG_FILE = 'config.json'
CACHE_FILE = 'magnets_cache.json'

HEADERS = {'User-Agent': 'Mozilla/5.0'}

# --- 认证相关 ---
def check_auth(username, password):
    config = load_config()
    return username == config.get('auth_user') and password == config.get('auth_pass')

def authenticate():
    return Response(
        'Authentication required', 401,
        {'WWW-Authenticate': 'Basic realm="Login"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if auth:
            try:
                scheme, credentials = auth.split(None, 1)
                if scheme.lower() == 'basic':
                    # 增加编码异常处理
                    try:
                        decoded = b64decode(credentials).decode('utf-8')
                        username, password = decoded.split(':', 1)
                        if check_auth(username, password):
                            return f(*args, **kwargs)
                    except (UnicodeDecodeError, ValueError) as e:
                        print(f"认证解码错误: {e}")
            except Exception as e:
                print(f"认证处理异常: {e}")
        # 调试用：打印未授权信息
        print("未授权访问请求")
        return authenticate()
    return decorated

# --- 配置读取保存 ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            'urls': [],
            'refresh_interval': 1,
            'auth_user': 'admin',
            'auth_pass': 'admin'
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"配置文件创建失败: {e}")
            # 开发环境下直接返回默认配置
            return default_config
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"配置文件读取失败: {e}")
        return {'urls': [], 'refresh_interval': 1, 'auth_user': 'admin', 'auth_pass': 'admin'}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# --- 缓存读取保存 ---
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_cache(items):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

# --- 编码磁力链接的dn参数 ---
def encode_magnet_dn(href):
    if not href.startswith("magnet:?"):
        return href
    def repl_dn(match):
        dn_value = match.group(1)
        dn_value = unquote(dn_value)
        dn_value_encoded = quote(dn_value, safe='')
        return f"dn={dn_value_encoded}"
    href = re.sub(r'dn=([^&]*)', repl_dn, href)
    return href

# --- 抓取磁力链接 ---
def fetch_magnets():
    items = []
    base_time = datetime.datetime.utcnow()
    config = load_config()
    urls = config.get('urls', [])
    for url in urls:
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')
            page_title = soup.title.text.strip() if soup.title else "磁力资源"
            for i, a_tag in enumerate(soup.find_all('a', href=True)):
                href = a_tag['href']
                if href.startswith('magnet:?xt=urn:btih:'):
                    href_fixed = encode_magnet_dn(href)
                    title = a_tag.text.strip() or page_title
                    pub_date = (base_time + datetime.timedelta(seconds=i)).strftime('%a, %d %b %Y %H:%M:%S +0000')
                    items.append({
                        'title': saxutils.escape(title),
                        'link': href_fixed,
                        'guid': href_fixed,
                        'pubDate': pub_date
                    })
        except Exception as e:
            print(f"爬取失败 {url}: {e}")
    return items

# --- 生成RSS ---
def generate_rss(items):
    now = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>磁力链接RSS订阅</title>
<link>http://localhost:5000/rss</link>
<description>自动抓取磁力链接</description>
<language>zh-cn</language>
<pubDate>{now}</pubDate>
'''
    for item in items:
        rss += f'''
<item>
<title>{item['title']}</title>
<link>{item['link']}</link>
<guid isPermaLink="false">{item['guid']}</guid>
<pubDate>{item['pubDate']}</pubDate>
</item>
'''
    rss += '</channel></rss>'
    return rss

# --- 自动刷新线程 ---
def auto_refresh():
    while True:
        config = load_config()
        interval = config.get('refresh_interval', 1)
        print(f"[定时刷新] {datetime.datetime.now()}, 间隔: {refresh_interval}分钟")
        items = fetch_magnets()
        save_cache(items)
        time.sleep(interval * 60)

# --- 路由部分 ---
@app.route('/')
@requires_auth
def index():
    config = load_config()
    urls = config.get('urls', [])
    refresh_interval = config.get('refresh_interval', 1)
    items = load_cache()
    message = request.args.get('msg', '')
    url_list_html = ''.join([
        f'''
        <li class="bg-gray-50 p-3 rounded-md flex justify-between items-center">
            <span class="text-sm text-gray-800 break-all">{url}</span>
            <form method="post" action="/del_url" onsubmit="return confirm('确认删除？')">
                <input type="hidden" name="del_url" value="{url}" />
                <button class="text-red-600 hover:underline text-sm">删除</button>
            </form>
        </li>
        ''' for url in urls
    ]) or '<li class="text-sm text-gray-500">暂无 URL</li>'

    item_list_html = ''.join([
        f'''
        <li class="bg-gray-50 p-3 rounded-md">
            <div class="font-medium text-gray-800">{item["title"]}</div>
            <div class="text-sm text-gray-600 break-all"><a href="{item["link"]}" class="hover:underline">{item["link"]}</a></div>
            <div class="text-xs text-gray-400">{item["pubDate"]}</div>
        </li>
        ''' for item in items
    ]) or '<li class="text-sm text-gray-500">暂无缓存数据</li>'

    html = f'''
    <!DOCTYPE html>
    <html lang="zh">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>磁力RSS管理</title>
      <script src="https://cdn.tailwindcss.com"></script>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
      <style>body {{ font-family: 'Inter', sans-serif; }}</style>
    </head>
    <body class="bg-gray-100 min-h-screen flex items-center justify-center p-6">
      <div class="bg-white w-full max-w-3xl shadow-xl rounded-2xl p-8">
        <h1 class="text-2xl font-bold text-gray-800 mb-6">磁力 RSS 管理</h1>

        <form method="post" action="/add_url" class="flex gap-2 mb-4">
          <input name="url" required placeholder="添加新 URL" class="flex-1 border px-4 py-2 rounded-md border-gray-300" />
          <button class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">添加</button>
        </form>

        <div class="mb-6">
          <h2 class="font-semibold text-lg text-gray-700 mb-2">当前 URL 列表（每 {refresh_interval} 分钟刷新）</h2>
          <form method="post" action="/set_interval" class="flex items-center gap-2 mb-4">
            <input type="number" name="interval" value="{refresh_interval}" min="1" class="w-20 border px-2 py-1 rounded border-gray-300" />
            <button class="bg-gray-700 text-white px-3 py-1 rounded hover:bg-gray-800">保存</button>
          </form>
          <ul class="space-y-2">
            {url_list_html}
          </ul>
        </div>

        <div>
          <h2 class="font-semibold text-lg text-gray-700 mb-2 flex justify-between items-center">
            缓存的磁力链接
            <a href="/refresh" class="text-blue-600 text-sm hover:underline">手动刷新</a>
          </h2>
          <ul class="space-y-2 max-h-64 overflow-y-auto pr-1">
            {item_list_html}
          </ul>
        </div>

        <div class="mt-8 p-4 bg-gray-50 rounded">
          <h3 class="font-semibold text-gray-700 mb-2">修改认证密码</h3>
          <form method="post" action="/change_password" class="flex gap-2 items-center">
            <input type="password" name="new_pass" placeholder="新密码" required class="border px-3 py-2 rounded border-gray-300 flex-1" />
            <button type="submit" class="bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600">修改</button>
          </form>
        </div>

        {'<div class="mt-4 text-green-600 font-medium">' + message + '</div>' if message else ''}
        <div class="mt-10 text-xs text-gray-400">Powered by Flask 磁力RSS爬虫</div>
      </div>
    </body>
    </html>
    '''
    return render_template_string(html, urls=urls, items=items, refresh_interval=refresh_interval, message=message)

@app.route('/add_url', methods=['POST'])
@requires_auth
def add_url():
    url = request.form.get('url', '').strip()
    if not url:
        return redirect(url_for('index', msg='URL不能为空'))
    config = load_config()
    urls = config.get('urls', [])
    if url not in urls:
        urls.append(url)
        config['urls'] = urls
        save_config(config)
        return redirect(url_for('index', msg='URL已添加'))
    return redirect(url_for('index', msg='URL已存在'))

@app.route('/del_url', methods=['POST'])
@requires_auth
def del_url():
    url = request.form.get('del_url')
    config = load_config()
    urls = config.get('urls', [])
    if url in urls:
        urls.remove(url)
        config['urls'] = urls
        save_config(config)
        return redirect(url_for('index', msg='URL已删除'))
    return redirect(url_for('index', msg='URL不存在'))

@app.route('/set_interval', methods=['POST'])
@requires_auth
def set_interval():
    try:
        interval = int(request.form.get('interval', 1))
        if interval < 1:
            raise ValueError
    except Exception:
        return redirect(url_for('index', msg='刷新间隔必须为正整数'))
    config = load_config()
    config['refresh_interval'] = interval
    save_config(config)
    return redirect(url_for('index', msg=f'刷新间隔设置为{refresh_interval}分钟'))

@app.route('/refresh')
@requires_auth
def refresh():
    items = fetch_magnets()
    save_cache(items)
    return redirect(url_for('index', msg=f'已手动刷新，获取{len(items)}个磁力链接'))

@app.route('/rss')
def rss_feed():
    items = load_cache()
    rss = generate_rss(items)
    return Response(rss.encode('utf-8'), content_type='application/rss+xml; charset=utf-8')

@app.route('/change_password', methods=['POST'])
@requires_auth
def change_password():
    new_pass = request.form.get('new_pass', '').strip()
    if not new_pass:
        return redirect(url_for('index', msg='密码不能为空'))
    config = load_config()
    config['auth_pass'] = new_pass
    save_config(config)
    return redirect(url_for('index', msg='密码已更新，请牢记新密码'))

if __name__ == '__main__':
    threading.Thread(target=auto_refresh, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
