import aiofiles
from PyPDF2 import PdfReader, PdfWriter
import os
from werkzeug.utils import secure_filename
from io import BytesIO

async def check_pdf_encryption(input_pdf: str) -> bool:
    """异步检查PDF文件是否加密"""
    try:
        async with aiofiles.open(input_pdf, 'rb') as file:
            content = await file.read()
            # 创建一个 BytesIO 对象，它支持 seek 操作
            pdf_stream = BytesIO(content)
            reader = PdfReader(pdf_stream)
            return reader.is_encrypted
    except Exception as e:
        print(f"检查加密状态时出错: {e}")
        return False

async def decrypt_pdf(input_pdf: str, output_pdf: str, password: str) -> tuple:
    """异步解密PDF文件"""
    try:
        async with aiofiles.open(input_pdf, 'rb') as file:
            content = await file.read()
            # 使用 BytesIO
            pdf_stream = BytesIO(content)
            reader = PdfReader(pdf_stream)
            
            # 先检查文件是否加密
            if not reader.is_encrypted:
                return False, "PDF文件未加密"
                
            try:
                if reader.decrypt(password):
                    writer = PdfWriter()
                    for page in reader.pages:
                        writer.add_page(page)
                    
                    # 直接写入文件而不是使用 aiofiles
                    with open(output_pdf, 'wb') as output:
                        writer.write(output)
                    return True, "解密成功"
                else:
                    return False, "密码不正确"
            except Exception as e:
                return False, f"解密失败: {str(e)}"
    except Exception as e:
        print(f"解密过程发生错误: {e}")
        return False, f"解密过程发生错误: {str(e)}"

async def save_uploaded_file(file, upload_folder: str) -> str:
    """异步保存上传的文件"""
    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    
    async with aiofiles.open(filepath, 'wb') as f:
        content = await file.read()
        await f.write(content)
    return filepath