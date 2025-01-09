# PDF Decrypt App

这是一个简单的网页应用程序，允许用户上传加密的PDF文件并解密它们。

## 项目结构

- `src/static/style.css`: 包含网页应用程序的CSS样式，定义HTML页面的布局和外观。
- `src/templates/index.html`: 主要HTML页面，用户可以在此上传PDF文件，并显示消息。
- `src/templates/decrypt.html`: 显示解密过程的结果，包括解密是否成功或密码是否错误的消息。
- `src/app.py`: 应用程序的入口点，设置Flask网络服务器，处理文件上传，并与`pdf_decrypt.py`工具集成以管理解密过程。
- `src/utils/pdf_decrypt.py`: 包含使用提供的密码解密PDF文件的逻辑，检查PDF是否加密并尝试解密，返回适当的状态。
- `requirements.txt`: 列出项目所需的依赖项，包括Flask和PyPDF2。

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
4. 在浏览器中访问 `http://127.0.0.1:5000`，上传您的PDF文件并输入密码进行解密。

## 许可证

此项目采用MIT许可证。