
---

# Magnet RSS Feed Generator / 磁力链接 RSS 订阅生成器

将热门磁力链接生成 RSS 订阅源，方便使用 RSS 阅读器自动获取最新资源。
Generate RSS feeds from popular magnet links, making it easy to get the latest resources automatically via RSS readers.

---

## 📦 项目简介 / Project Overview

本项目提供一个简单的 Flask Web 服务，可以定期从磁力搜索网站获取热门资源（如电影、剧集、综艺等），并将其转换为标准的 RSS Feed 格式。
This project offers a simple Flask web service that periodically fetches popular resources (movies, TV shows, variety shows, etc.) from magnet search websites and converts them into standard RSS feed format.

---

## ✨ 功能特点 / Features

* 🧲 自动抓取热门磁力链接 / Automatically scrape popular magnet links
* 📰 生成符合 RSS 2.0 标准的订阅源 / Generate RSS 2.0 compliant feeds
* 📦 Docker 支持，部署方便 / Docker support for easy deployment
* ⏱ 支持定时刷新内容（可拓展） / Supports scheduled content refresh (extensible)

---

## 🚀 快速开始 / Quick Start

### 🔧 安装依赖（本地运行）/ Install dependencies (local run)

```bash
git clone https://github.com/YOUR_USERNAME/magnet-rss.git
cd magnet-rss
pip install -r requirements.txt
python app.py
```

默认运行在 [http://localhost:5000](http://localhost:5000)
Runs by default at [http://localhost:5000](http://localhost:5000)

---

### 🐳 使用 Docker 部署 / Deploy with Docker


```bash
# 在其他系统中编译
# Bulid with Docker in other systems.
docker build -t 5breeze/magnet-rss .
```

```bash
#直接拉取镜像使用（当前支持AMD64、arm64、armv7）
# Run directly.
docker run -d -p 5000:5000 --name magnet-rss 5breeze/magnet-rss:main

```

---

## 📡 RSS 订阅地址示例 / RSS Feed URL Example

启动服务后，访问以下地址即可获取 RSS：
After starting the service, access the URL below to get the RSS feed:

```
http://localhost:5000/rss
```

你可以在 RSS 阅读器中添加此链接以订阅磁力资源更新。
Add this URL to your RSS reader to subscribe to magnet link updates.

---

## 🛠 管理界面 / Admin Interface

在根目录下存在管理界面，可自由定义解析网站、刷新时间，
登录初始用户名和密码为：admin / admin

There is an admin interface in the root directory allowing you to configure parsing sites and refresh intervals.
Default login username and password: **admin / admin**

---

## 📁 项目结构 / Project Structure

```
magnet-rss/
├── app.py              # Flask 主程序 / Flask main app
├── requirements.txt    # 依赖列表 / Dependencies list
├── Dockerfile          # Docker 构建文件 / Docker build file
└── README.md           # 项目说明文档 / Project documentation
```

---

## 🛠 技术栈 / Tech Stack

* Python 3.10
* Flask
* feedgen（生成 RSS）/ feedgen (RSS generation)
* requests / BeautifulSoup（网页抓取）/ requests & BeautifulSoup (web scraping)

---

## 📄 License

MIT License

---

