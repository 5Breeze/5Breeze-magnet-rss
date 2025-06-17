# Magnet RSS Feed Generator

将热门磁力链接生成 RSS 订阅源，方便使用 RSS 阅读器自动获取最新资源。

## 📦 项目简介

本项目提供一个简单的 Flask Web 服务，可以定期从磁力搜索网站获取热门资源（如电影、剧集、综艺等），并将其转换为标准的 RSS Feed 格式。

## ✨ 功能特点

- 🧲 自动抓取热门磁力链接
- 📰 生成符合 RSS 2.0 标准的订阅源
- 📦 Docker 支持，部署方便
- ⏱ 支持定时刷新内容（可拓展）

---

## 🚀 快速开始

### 🔧 安装依赖（本地运行）

```bash
git clone https://github.com/YOUR_USERNAME/magnet-rss.git
cd magnet-rss
pip install -r requirements.txt
python app.py
````

默认运行在 [http://localhost:5000](http://localhost:5000)

---

### 🐳 使用 Docker 部署

```bash
docker build -t yourname/magnet-rss .
docker run -d -p 5000:5000 yourname/magnet-rss
```

---

## 📡 RSS 订阅地址示例

一旦服务启动，访问以下地址即可获取 RSS：

```
http://localhost:5000/rss
```

你可以在 RSS 阅读器中添加这个链接来订阅磁力资源更新。

---

## 📁 项目结构

```
magnet-rss/
├── app.py              # Flask 主程序
├── requirements.txt    # 依赖列表
├── Dockerfile          # Docker 构建文件
└── README.md           # 项目说明文档
```

---

## 🛠 技术栈

* Python 3.10
* Flask
* feedgen（生成 RSS）
* requests / BeautifulSoup（网页抓取）

---

## 📄 License

MIT License

---
