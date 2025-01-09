from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from celery import Celery
from celery.schedules import crontab
import os
import secrets
from datetime import datetime, timedelta
from utils.pdf_decrypt import check_pdf_encryption, decrypt_pdf, save_uploaded_file
from urllib.parse import unquote, quote
import aiofiles
import asyncio

app = FastAPI()

# 静态文件和模板配置
app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")

# Celery配置
celery_app = Celery('tasks', broker='redis://localhost:6379/0')

# 文件夹配置
UPLOAD_FOLDER = 'src/uploads'
DOWNLOAD_FOLDER = 'src/downloads'

# 文件映射存储
FILE_MAPPINGS = {}

# 在文件顶部添加锁字典
file_locks = {}

def generate_secure_token():
    """生成安全的随机token"""
    return secrets.token_urlsafe(32)  # 生成32字节的安全随机token

@app.on_event("startup")
async def startup_event():
    """创建必要的文件夹"""
    for folder in [UPLOAD_FOLDER, DOWNLOAD_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)

@app.on_event("shutdown")
async def shutdown_event():
    """服务器关闭时清理所有文件"""
    # 清理下载文件夹
    for token, file_info in FILE_MAPPINGS.copy().items():
        file_path = os.path.join(DOWNLOAD_FOLDER, file_info['internal_filename'])
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            del FILE_MAPPINGS[token]
        except Exception as e:
            print(f"清理文件时出错: {e}")
    
    # 清理上传文件夹中的所有文件
    for filename in os.listdir(UPLOAD_FOLDER):
        try:
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"清理上传文件时出错: {e}")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):  # 确保添加 Request 参数的类型注解
    return templates.TemplateResponse(
        "index.html", 
        {"request": request}  # 确保传递 request 对象给模板
    )

@app.post("/decrypt")
async def decrypt(
    request: Request,
    file: UploadFile = File(...),
    password: str = Form(...),
):
    # 解码中文文件名并保留原始文件名
    original_filename = unquote(file.filename)
    if not original_filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="请上传PDF文件")

    # 保存上传的文件（使用临时文件名）
    input_path = await save_uploaded_file(file, UPLOAD_FOLDER)
    
    # 首先检查文件是否加密
    is_encrypted = await check_pdf_encryption(input_path)
    if not is_encrypted:
        return templates.TemplateResponse(
            "decrypt.html",
            {"request": request, "success": False, "incorrect_password": False}
        )

    # 生成token作为内部存储文件名
    token = generate_secure_token()
    
    # 构建文件名...
    original_name = os.path.splitext(original_filename)[0]
    download_filename = f"{original_name}_decrypted.pdf"
    internal_filename = f"{token}.pdf"
    
    output_path = os.path.join(DOWNLOAD_FOLDER, internal_filename)

    # 解密处理...
    success, message = await decrypt_pdf(input_path, output_path, password)
    
    # 删除上传的原始加密文件
    try:
        os.remove(input_path)
    except Exception as e:
        print(f"删除上传文件时出错: {e}")
        
    if success:
        FILE_MAPPINGS[token] = {
            'internal_filename': internal_filename,  # 内部存储文件名
            'download_filename': download_filename,  # 用户下载时显示的文件名
            'expire_time': datetime.now() + timedelta(minutes=30)
        }
        return templates.TemplateResponse(
            "decrypt.html",
            {"request": request, "success": True, "output_pdf": token}
        )
    return templates.TemplateResponse(
        "decrypt.html",
        {"request": request, "success": False, "incorrect_password": message == "密码不正确"}
    )

@app.get("/download/{token}")
async def download_file(token: str):
    if token not in FILE_MAPPINGS:
        raise HTTPException(status_code=404, detail="Invalid download link")
    
    # 为每个token创建一个锁
    if token not in file_locks:
        file_locks[token] = asyncio.Lock()
    
    async with file_locks[token]:
        try:
            if token not in FILE_MAPPINGS:
                raise HTTPException(status_code=404, detail="Invalid download link")
            
            file_info = FILE_MAPPINGS[token]
            if datetime.now() > file_info['expire_time']:
                del FILE_MAPPINGS[token]
                raise HTTPException(status_code=410, detail="Download link has expired")
            
            file_path = os.path.join(DOWNLOAD_FOLDER, file_info['internal_filename'])
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")
            
            # 使用 aiofiles 异步读取文件内容
            async with aiofiles.open(file_path, 'rb') as file:
                content = await file.read()
                
            return Response(
                content=content,
                media_type='application/pdf',
                headers={
                    'Content-Disposition': f'attachment; filename*=UTF-8\'\'{quote(file_info["download_filename"])}'
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"下载文件时出错: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
        finally:
            if token in file_locks:
                del file_locks[token]

# Celery定时任务
@celery_app.task
def clean_expired_files():
    current_time = datetime.now()
    expired_tokens = [
        token for token, info in FILE_MAPPINGS.items()
        if current_time > info['expire_time']
    ]
    for token in expired_tokens:
        file_info = FILE_MAPPINGS[token]
        file_path = os.path.join(DOWNLOAD_FOLDER, file_info['internal_filename'])
        if os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except Exception as e:
                print(f'Error deleting file: {e}')
        del FILE_MAPPINGS[token]

# 配置Celery定时任务
celery_app.conf.beat_schedule = {
    'clean-expired-files': {
        'task': 'main.clean_expired_files',
        'schedule': crontab(minute='*/30'),
    },
}

async def save_uploaded_file(file, upload_folder: str) -> str:
    """异步保存上传的文件"""
    # 解码中文文件名
    original_filename = unquote(file.filename)
    
    # 生成一个唯一的文件名用于存储，但保留原始扩展名
    temp_filename = f"{secrets.token_hex(16)}{os.path.splitext(original_filename)[1]}"
    filepath = os.path.join(upload_folder, temp_filename)
    
    async with aiofiles.open(filepath, 'wb') as f:
        content = await file.read()
        await f.write(content)
    return filepath

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=80, workers=4)