# PDF Decrypt App

这是一个简单的网页应用程序，允许用户上传加密的PDF文件并解密它们。

## 项目结构

主要组件说明：

- `app.py`: FastAPI应用程序入口，处理文件上传和下载
- `static/style.css`: 网页样式定义
- `templates/`: 包含网页模板文件
- `utils/pdf_decrypt.py`: 提供PDF文件加密检查和解密功能
- `downloads/` 和 `uploads/`: 用于临时存储文件的目录

## 安装和使用

1. 克隆此存储库。
2. 安装依赖项：
   ```
   pip install -r requirements.txt
   ```
3. 运行应用程序：
   ```
   python src/app.py
   ```
4. 在浏览器中访问 `http://127.0.0.1:80`，上传您的PDF文件并输入密码进行解密。
## 注意事项
项目基于python3.10.7实现
## 许可证

此项目采用MIT许可证。
