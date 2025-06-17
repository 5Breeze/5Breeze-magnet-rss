FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制依赖和源码
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 暴露端口
EXPOSE 5000

# 启动应用
CMD ["python", "app.py"]
