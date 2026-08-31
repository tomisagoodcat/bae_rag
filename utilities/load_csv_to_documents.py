"""
CSV到LlamaIndex Documents转换模块
用于Jupyter notebook导入使用
"""


import os
import glob
from typing import List, Union
from llama_index.core import Document
import fitz  # PyMuPDF
import pandas as pd
 
import re
 
 
# 配置路径
#ABSTRACT_DIR = "."  # 默认当前目录，可根据需要修改

def load_csv_to_documents(csv_path="extracted_papers.csv", abstract_dir=None):
    """
    从CSV文件创建LlamaIndex Documents
    
    Args:
        csv_path: CSV文件名，默认"extracted_papers.csv"
        abstract_dir: CSV文件所在目录，默认使用ABSTRACT_DIR
    
    Returns:
        list: Document对象列表
    """
    # 确定文件路径
    base_dir = abstract_dir  
    full_path = os.path.join(base_dir, csv_path)
    print(full_path)
    # 读取CSV
    df = pd.read_csv(full_path)
    print(f"📖 读取CSV: {len(df)} 行, 列: {list(df.columns)}")
    
    # 转换为Documents
    documents = []
    for idx, row in df.iterrows():
        text = str(row.get('abstract', '')).strip()
        if text:  # 跳过空text
            documents.append(Document(
                text=text,
                metadata={
                    'title': str(row.get('title', '')),
                    'author': str(row.get('author', '')),
                    'keywords': str(row.get('keywords', '')),
                    'source_file': str(row.get('source_file', '')),
                    'doc_id': f"paper_{idx}"
                }
            ))
    
    print(f"✅ 创建Documents: {len(documents)} 个")
    return documents
def load_pdf_to_documents(pdf_path: Union[str, List[str]], pdf_dir: str = None) -> List[Document]:
    """
    从PDF文件创建LlamaIndex Documents
    
    Args:
        pdf_path: PDF文件路径、路径列表或通配符模式 (如 "*.pdf")
        pdf_dir: PDF文件所在目录，默认当前目录
    
    Returns:
        list: Document对象列表
    """
    if pdf_dir is None:
        pdf_dir = os.getcwd()
    
    # 获取PDF文件列表
    pdf_files = []
    if isinstance(pdf_path, list):
        pdf_files = [os.path.join(pdf_dir, f) if not os.path.isabs(f) else f for f in pdf_path]
    elif isinstance(pdf_path, str):
        if "*" in pdf_path or "?" in pdf_path:
            # 通配符模式
            pattern = os.path.join(pdf_dir, pdf_path) if not os.path.isabs(pdf_path) else pdf_path
            pdf_files = glob.glob(pattern)
        else:
            # 单个文件
            full_path = os.path.join(pdf_dir, pdf_path) if not os.path.isabs(pdf_path) else pdf_path
            pdf_files = [full_path]
    
    # 过滤存在的PDF文件
    pdf_files = [f for f in pdf_files if os.path.exists(f) and f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"❌ 未找到PDF文件: {pdf_path}")
        return []
    
    print(f"📖 发现 {len(pdf_files)} 个PDF文件")
    
    # 提取文档
    documents = []
    total_pages = 0
    
    for file_path in pdf_files:
        try:
            filename = os.path.basename(file_path)
            print(f"🔄 处理: {filename}")
            
            # 使用PyMuPDF读取PDF
            doc = fitz.open(file_path)
            file_pages = len(doc)
            
            # 提取全文
            full_text = ""
            for page_num in range(file_pages):
                try:
                    page_text = doc[page_num].get_text()
                    if page_text.strip():
                        full_text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                except:
                    continue
            
            doc.close()
            
            if full_text.strip():
                documents.append(Document(
                    text=full_text.strip(),
                    metadata={
                        'source_file': filename,
                        'file_path': file_path,
                        'total_pages': file_pages,
                        'doc_id': f"{filename.replace('.pdf', '')}"
                    }
                ))
                total_pages += file_pages
                print(f"   ✅ 完成: {file_pages} 页")
            else:
                print(f"   ⚠️ 跳过: 无文本内容")
                
        except Exception as e:
            print(f"   ❌ 失败: {str(e)}")
            continue
    
    print(f"✅ 创建Documents: {len(documents)} 个 (总计 {total_pages} 页)")
    return documents


def load_markdown_to_documents(
    md_path: Union[str, List[str]],
    md_dir: str = None,
    encoding: str = "utf-8",
    normalize_headers: bool = False,
) -> List[Document]:
    """
    从 Markdown 文件创建 LlamaIndex Documents（与 load_pdf_to_documents 返回形态对齐）

    Args:
        md_path: Markdown 文件路径、路径列表或通配符模式 (如 "*.md")
        md_dir: 文件所在目录，默认当前工作目录
        encoding: 读取编码，默认 "utf-8"
        normalize_headers: 是否将常见章节标题自动标准化为 Markdown 标题（行首加 "# "）

    Returns:
        List[Document]: 每个文件对应一个 Document(text=全文字符串, metadata=文件级信息)
    """
    if md_dir is None:
        md_dir = os.getcwd()

    # 1) 解析输入，得到文件列表
    md_files: List[str] = []
    if isinstance(md_path, list):
        md_files = [os.path.join(md_dir, f) if not os.path.isabs(f) else f for f in md_path]
    elif isinstance(md_path, str):
        if "*" in md_path or "?" in md_path:
            # 通配符
            pattern = os.path.join(md_dir, md_path) if not os.path.isabs(md_path) else md_path
            md_files = glob.glob(pattern)
        else:
            # 单文件
            full_path = os.path.join(md_dir, md_path) if not os.path.isabs(md_path) else md_path
            md_files = [full_path]

    # 2) 过滤存在的 .md 文件
    md_files = [f for f in md_files if os.path.exists(f) and f.lower().endswith((".md", ".markdown"))]

    if not md_files:
        print(f"❌ 未找到Markdown文件: {md_path}")
        return []

    print(f"📝 发现 {len(md_files)} 个Markdown文件")

    # 3) 可选：章节标题标准化（把常见章节孤立行变为 Markdown 标题）
    section_regex = re.compile(
        r"^\s*(摘要|引言|材料与方法|实验方法|方法|结果|讨论|结论|致谢|参考文献|相关工作|综述|评述"
        r"|Abstract|Introduction|Materials?\s*(and|&)\s*Methods?|Methods?|Results?|Discussion|Conclusions?|Acknowledg(e)?ments?|References|Related\s*Work|Review)\s*$",
        re.IGNORECASE
    )

    def normalize_md_headers(text: str) -> str:
        lines = text.splitlines()
        out = []
        for ln in lines:
            # 已经是标题就不动（以 # 开头）
            if ln.lstrip().startswith("#"):
                out.append(ln)
                continue
            # 孤立章节名 → 标题化
            if section_regex.match(ln.strip()):
                out.append("# " + ln.strip())
            else:
                out.append(ln)
        return "\n".join(out)

    # 4) 读取并组装 Document 列表
    documents: List[Document] = []
    for file_path in md_files:
        try:
            filename = os.path.basename(file_path)
            with open(file_path, "r", encoding=encoding) as f:
                raw_text = f.read()

            text = normalize_md_headers(raw_text) if normalize_headers else raw_text

            # 保持与 load_pdf_to_documents 类似的 metadata 形态
            doc = Document(
                text=text.strip(),
                metadata={
                    "source_file": filename,
                    "file_path": file_path,
                    "doc_id": os.path.splitext(filename)[0],
                    "format": "markdown",
                },
            )
            documents.append(doc)
            print(f"   ✅ 完成: {filename}")
        except Exception as e:
            print(f"   ❌ 读取失败: {file_path} | {e}")

    print(f"✅ 创建Documents: {len(documents)} 个")
    return documents
