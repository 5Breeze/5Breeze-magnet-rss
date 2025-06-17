import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import threading
import time
from flask import Flask, Response, render_template_string, request, redirect, url_for, abort
import xml.sax.saxutils as saxutils
import re
from urllib.parse import quote, unquote
from functools import wraps
from base64 import b64decode

app = Flask(__name__)

CONFIG_FILE = 'config.json'
CACHE_FILE = 'magnets_cache.json'

HEADERS = {
    'User-Agent': 'Mozilla/5.0'
}

# --- 认证装饰器 ---
def check_auth(username, password):
    config = load_config()
    return username == config.get('auth_user') and password == config.get('auth_pass')

def authenticate():
    return Response(
        '请提供认证信息', 401,
        {'WWW-Authenticate': 'Basic realm="登录"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if auth:
            try:
                scheme, credentials = auth.split(None, 1)
                if scheme.lower() == 'basic':
                    decoded = b64decode(credentials).decode('utf-8')
                    username, password = decoded.split(':', 1)
                    if check_auth(username, password):
                        return f(*args, **kwargs)
            except Exception:
                pass
        return authenticate()
    return decorated

# --- 配置相关 ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            'urls': [],
            'refresh_interval': 1,   # 单位：分钟
            'auth_user': 'admin',
            'auth_pass': 'admin'
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        return default_config
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# --- 缓存相关 ---
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_cache(items):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

# --- 磁力链接dn参数编码 ---
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
<link>{saxutils.escape(item['link'])}</link>
<guid isPermaLink="false">{saxutils.escape(item['guid'])}</guid>
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
        print(f"[定时刷新] {datetime.datetime.now()}, 间隔: {interval}分钟")
        items = fetch_magnets()
        save_cache(items)
        time.sleep(interval * 60)

# --- 路由 ---
@app.route('/')
@requires_auth
def index():
    config = load_config()
    urls = config.get('urls', [])
    refresh_interval = config.get('refresh_interval', 1)
    items = load_cache()
    message = request.args.get('msg', '')
    html = '''
    <html lang="zh">
    <head>
      <meta charset="utf-8" />
      <title>磁力RSS管理界面</title>
      <style>
        body { font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif; margin: 30px; background: #f0f2f5; }
        h1, h2, h3 { color: #333; }
        input[type=text], input[type=number] { padding: 6px; width: 300px; margin-right:10px; }
        button { padding: 6px 12px; background: #0078d7; color: white; border: none; cursor: pointer; }
        button:hover { background: #005a9e; }
        ul { list-style-type: none; padding-left: 0; }
        li { background: white; margin-bottom: 8px; padding: 10px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        a { color: #0078d7; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .small { font-size: 0.85em; color: #666; }
        .footer { margin-top: 40px; font-size: 0.85em; color: #999; }
        .message { margin: 15px 0; color: green; }
        .url-list { max-height: 200px; overflow-y: auto; }
        .magnet-list { max-height: 300px; overflow-y: auto; }
        form.inline { display: inline; }
      </style>
    </head>
    <body>
      <h1>磁力RSS管理界面</h1>
      
      <form method="post" action="/add_url">
        <input name="url" placeholder="输入新的URL" required />
        <button type="submit">添加URL</button>
      </form>

      <h3>当前URL列表（刷新间隔：
        <form method="post" action="/set_interval" style="display:inline;">
          <input type="number" name="interval" value="{{refresh_interval}}" min="1" style="width: 60px;" required /> 分钟
          <button type="submit">保存</button>
        </form>
      分钟）</h3>

      <ul class="url-list">
      {% for u in urls %}
        <li>{{ u }}
          <form method="post" action="/del_url" class="inline" onsubmit="return confirm('确认删除此URL吗？');">
            <input type="hidden" name="del_url" value="{{ u }}">
            <button type="submit" style="background:#d9534f;">删除</button>
          </form>
        </li>
      {% else %}
        <li>暂无URL</li>
      {% endfor %}
      </ul>

      <h3>缓存的磁力链接 <button onclick="location.href='/refresh'">手动刷新</button></h3>
      <ul class="magnet-list">
      {% for item in items %}
        <li><b>{{ item.title }}</b><br/>
            链接：<a href="{{ item.link }}">{{ item.link }}</a><br/>
            时间：{{ item.pubDate }}
        </li>
      {% else %}
        <li>暂无缓存数据，请点击刷新按钮获取。</li>
      {% endfor %}
      </ul>
      {% if message %}
      <p class="message">{{ message }}</p>
      {% endif %}
      <div class="footer">Powered by Flask 磁力RSS爬虫</div>
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
    if not url:
        return redirect(url_for('index', msg='未指定要删除的URL'))
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
    return redirect(url_for('index', msg=f'刷新间隔设置为{interval}分钟'))

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

if __name__ == '__main__':
    threading.Thread(target=auto_refresh, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
