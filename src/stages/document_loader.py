"""Markdown load, structural split, semantic splitter (from 1_2_0_2 module1)."""
from __future__ import annotations

# ==================== 导入依赖 ====================
from typing import List, Optional, Callable, Dict, Any
from llama_index.core import Document
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.schema import BaseNode, TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.llms.deepseek import DeepSeek
import os
import re
import nest_asyncio
from datetime import datetime
from tqdm import tqdm
import traceback

# 解决Jupyter/异步环境中的事件循环嵌套问题
nest_asyncio.apply()

# ==================== 模块1: 文档解析与元数据提取 ====================

import json

def load_agent_metadata(markdown_path: str) -> dict:
    """
    加载Agent生成的元数据文件
    
    优先级：
    1. JSON文件（Agent生成）
    2. 默认值（如果没有Agent元数据）
    
    Args:
        markdown_path: Markdown文件路径
        
    Returns:
        dict: DC元数据字典
    """
    base = os.path.splitext(markdown_path)[0]
    json_path = f"{base}_metadata.json"
    
    # 尝试读取Agent生成的JSON
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 验证必需字段
            required_fields = ['dc_title', 'dc_author', 'dc_publisher']
            if all(field in metadata for field in required_fields):
                return metadata
            else:
                print(f"⚠️ 元数据文件缺少必需字段: {json_path}")
        
        except Exception as e:
            print(f"⚠️ 读取元数据失败 {json_path}: {e}")
    
    # 如果没有Agent元数据，返回默认值
    filename = os.path.basename(markdown_path)
    print(f"⚠️ 使用默认元数据: {filename}")
    
    return {
        'dc_title': filename.replace('.md', ''),
        'dc_author': 'Unknown',
        'dc_publisher': 'Unknown',
        'dc_creator': 'Unknown',
        'dc_type': 'Research Article',
        'dc_language': 'unknown',
        'dcterms_issued': 'Unknown',
        'dcterms_identifier': f'local:{filename}',
        'source': 'default',
        'source_filename': filename,
        'processed_at': datetime.now().isoformat()
    }


def list_markdown_documents(directory_path: str) -> List[str]:
    """Return sorted .md filenames in a directory without loading content."""
    if not os.path.isdir(directory_path):
        return []
    return sorted(
        filename
        for filename in os.listdir(directory_path)
        if filename.endswith(".md")
    )


def count_markdown_documents(directory_path: str) -> int:
    """Count .md files in a directory without loading content."""
    return len(list_markdown_documents(directory_path))


def effective_document_count(directory_path: str, max_docs: Any) -> int:
    """Apply max_docs cap to the markdown file count."""
    total = count_markdown_documents(directory_path)
    if isinstance(max_docs, int) and max_docs > 0:
        return min(total, max_docs)
    return total


def load_markdown_with_agent_metadata(directory_path: str) -> List[Document]:
    """
    加载Markdown文件并使用Agent生成的元数据
    
    工作流程：
    1. 遍历目录中的.md文件
    2. 读取文件内容
    3. 加载对应的Agent元数据（_metadata.json）
    4. 创建Document对象
    
    Args:
        directory_path: Markdown文件所在目录
        
    Returns:
        List[Document]: 文档对象列表
    """
    documents = []
    
    print(f"\n{'='*60}")
    print(f"📂 加载Markdown文件（使用Agent元数据）")
    print(f"{'='*60}\n")
    
    for filename in os.listdir(directory_path):
        if not filename.endswith('.md'):
            continue
        
        file_path = os.path.join(directory_path, filename)
        
        # 读取Markdown内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ 读取文件失败 {filename}: {e}")
            continue
        
        # 👇 新方法：读取Agent元数据
        dc_metadata = load_agent_metadata(file_path)
        
        # 创建Document对象
        doc = Document(
            text=content,
            metadata={'filename': filename, **dc_metadata}
        )
        documents.append(doc)
        
        # 打印验证信息
        print(f"📄 {filename}")
        print(f"   标题: {dc_metadata.get('dc_title', 'Unknown')[:60]}")
        print(f"   作者: {dc_metadata.get('dc_author', 'Unknown')}")
        print(f"   来源: {dc_metadata.get('source', 'Unknown')}")
        if dc_metadata.get('dc_subject'):
            print(f"   关键词: {dc_metadata['dc_subject']}")
        print()
    
    print(f"✅ 成功加载 {len(documents)} 个文档\n")
    return documents


def parse_markdown_headers(text: str) -> dict:
    """
    解析Markdown标题层级结构
    
    功能：
    - 识别所有Markdown标题（#, ##, ###等）
    - 构建完整的层级路径（如："第一章 > 1.1节 > 1.1.1小节"）
    - 记录每个标题在文本中的字符位置
    
    Args:
        text (str): Markdown格式的文本内容
        
    Returns:
        dict: {字符位置: 标题路径} 的映射
    """
    lines = text.split('\n')
    position_to_header = {}  # 位置→标题路径映射
    header_stack = []         # 维护当前标题层级栈
    char_position = 0         # 当前字符位置
    
    for line in lines:
        if line.strip().startswith('#'):
            # 计算标题级别（#的数量）
            level = len(line) - len(line.lstrip('#'))
            # 提取标题文本
            title = line.lstrip('#').strip()
            
            # 维护标题栈（移除同级或更低级的标题）
            header_stack = [h for h in header_stack if h[0] < level]
            header_stack.append((level, title))
            
            # 构建完整标题路径（用 > 连接）
            header_path = ' > '.join([h[1] for h in header_stack])
            position_to_header[char_position] = header_path
        
        char_position += len(line) + 1
    
    return position_to_header


def split_by_structure(text: str, chunk_size: int = 800) -> List[str]:
    """
    按Markdown结构智能分割文本
    
    分割策略：
    1. 优先在标题处分割（保持章节完整性）
    2. 其次在段落边界分割（保持段落完整性）
    3. 避免创建过小或过大的块
    
    Args:
        text (str): 待分割的Markdown文本
        chunk_size (int): 目标块大小（字符数），默认800
        
    Returns:
        List[str]: 分割后的文本块列表
    """
    lines = text.split('\n')
    chunks = []       # 最终的文本块
    current = []      # 当前正在构建的块
    size = 0          # 当前块大小
    
    for line in lines:
        line_size = len(line) + 1
        
        # 策略1：在标题处分割（当前块>200字符时）
        if line.strip().startswith('#') and current and size > 200:
            chunks.append('\n'.join(current))
            current, size = [line], line_size
        else:
            current.append(line)
            size += line_size
            
            # 策略2：块超过目标大小时，在空行（段落边界）处分割
            if size > chunk_size and line.strip() == '':
                chunks.append('\n'.join(current[:-1]))
                current, size = [], 0
    
    # 添加最后一个块
    if current:
        chunks.append('\n'.join(current))
    
    return chunks


def create_nodes_with_metadata(doc: Document) -> List[TextNode]:
    """
    创建节点并继承DC元数据
    
    功能：
    1. 使用split_by_structure按结构分割文本
    2. 为每个文本块创建TextNode
    3. 将Document的DC元数据传递给每个Node
    4. 添加块级元数据（filename, chunk_id）
    
    Args:
        doc (Document): 包含文本和DC元数据的Document对象
        
    Returns:
        List[TextNode]: 节点列表，每个包含文本和完整元数据
    """
    # 按结构分割文本
    text_chunks = split_by_structure(doc.text, chunk_size=800)
    nodes = []
    
    # 提取文档级DC元数据（将传递给所有节点）
    doc_dc = {
        k: v for k, v in doc.metadata.items() 
        if k.startswith('dc_') or k.startswith('dcterms_') or k in ['source_filename', 'processed_at']
    }
    
    # 为每个chunk创建节点
    for i, chunk in enumerate(text_chunks):
        if chunk.strip():
            node = TextNode(
                text=chunk,
                metadata={
                    'filename': doc.metadata.get('filename', ''),
                    'chunk_id': i,
                    **doc_dc  # 继承DC元数据
                }
            )
            nodes.append(node)
    
    return nodes


def add_header_paths(nodes: List[BaseNode], original_text: str) -> List[BaseNode]:
    """
    为节点添加标题路径（header_path）
    
    功能：
    1. 解析原文中的所有标题
    2. 为每个节点定位其在原文中的位置
    3. 分配最近的上级标题作为header_path
    
    Args:
        nodes (List[BaseNode]): 节点列表
        original_text (str): 原始文档文本
        
    Returns:
        List[BaseNode]: 添加了header_path的节点列表
    """
    # 解析所有标题及其位置
    position_to_header = parse_markdown_headers(original_text)
    
    # 获取默认标题（文档第一个标题）
    default_title = "Unknown"
    for line in original_text.split('\n')[:20]:
        if line.strip().startswith('#'):
            default_title = line.lstrip('#').strip()
            break
    
    # 为每个节点分配header_path
    for node in nodes:
        if isinstance(node, TextNode):
            if node.metadata is None:
                node.metadata = {}
            
            # 简化定位：使用节点文本前50字符匹配
            node_text = node.get_content()
            clean_node = re.sub(r'\s+', ' ', node_text[:50].strip())
            clean_original = re.sub(r'\s+', ' ', original_text)
            pos = clean_original.find(clean_node)
            
            if pos >= 0:
                # 找到最近的标题
                best_header = default_title
                for header_pos, header in sorted(position_to_header.items(), reverse=True):
                    if header_pos <= pos:
                        best_header = header
                        break
                node.metadata['header_path'] = best_header
            else:
                node.metadata['header_path'] = default_title
    
    return nodes


class SafeSemanticSplitter(SemanticSplitterNodeParser):
    """
    语义分割器（带section_role推断）
    
    功能：
    1. 基于语义相似度的智能分割（继承自父类）
    2. 为每个节点推断section_role（新增）
    3. 保留DC元数据在分割过程中不丢失（新增）
    """
    
    def __init__(self, embed_model=None, section_role_inferrer=None, **kwargs):
        """
        初始化语义分割器
        
        Args:
            embed_model: 嵌入模型（默认使用中文BCE模型）
            section_role_inferrer: section_role推断函数
            **kwargs: 其他参数（similarity_threshold, chunk_size等）
        """
        if embed_model is None:
            embed_model = HuggingFaceEmbedding(model_name="maidalun1020/bce-embedding-base_v1")
        
        super().__init__(embed_model=embed_model, **kwargs)
        
        # 保存section_role推断器
        object.__setattr__(self, '_section_role_inferrer', section_role_inferrer)
    
    def get_nodes_from_documents(self, documents: List[Document], **kwargs) -> List[BaseNode]:
        """
        从文档生成节点，执行语义分割并推断section_role
        
        处理流程：
        1. 调用父类方法执行语义分割
        2. 为每个节点推断section_role
        3. 确保元数据保留
        
        Args:
            documents: 文档列表
            
        Returns:
            List[BaseNode]: 增强后的节点列表
        """
        # 步骤1：执行语义分割
        nodes = super().get_nodes_from_documents(documents, **kwargs)
        
        # 步骤2：获取section_role推断器
        inferrer = getattr(self, '_section_role_inferrer', None)
        if not inferrer:
            return nodes
        
        # 步骤3：为每个节点添加section_role
        enhanced = []
        for node in nodes:
            if isinstance(node, TextNode):
                text = node.get_content()
                metadata = node.metadata or {}
                header = metadata.get("header_path", "")
                
                # 只在没有section_role时才推断
                if "section_role" not in metadata:
                    try:
                        # 调用推断器
                        role = inferrer(text, header)
                        metadata["section_role"] = role
                        node.metadata = metadata
                    except Exception as e:
                        print(f"⚠️ section_role推断失败: {e}")
            enhanced.append(node)
        
        return enhanced


def create_section_inferrer(llm):
    """
    创建混合式section_role推断器（规则+LLM）
    
    推断策略：
    1. 优先使用规则匹配（快速，覆盖80%标准标题）
    2. 规则失败时使用LLM推断（准确，处理20%疑难标题）
    
    Args:
        llm: LangChain的ChatOpenAI实例（DeepSeek）
        
    Returns:
        function: 推断函数，接受(text, header_path)返回section_role
    """
    import re
    
    # 统计LLM调用次数（可选，用于监控）
    llm_call_count = {'count': 0}
    
    def infer(text: str, header: str) -> str:
        """
        推断section_role（混合方案）
        
        Args:
            text (str): 节点文本内容（前200字符）
            header (str): 标题路径
            
        Returns:
            str: section_role类型
        """
        # ========== 第一层：规则匹配（快速，免费）==========
        header_lower = header.lower()
        text_lower = text[:200].lower()
        
        # ===== Abstract（摘要）=====
        if any(k in header_lower for k in [
            'abstract', '摘要', '概述', 'summary', '文摘'
        ]):
            return 'Abstract'
        
        # ===== Introduction（引言）=====
        if any(k in header_lower for k in [
            'introduction', '引言', '前言', '绪论', '背景', 
            'background', '研究背景', '概况', 'overview'
        ]) or re.match(r'^1\.', header_lower):  # 数字模式：1.x
            return 'Introduction'
        
        # ===== Methods_Materials（方法与材料）=====
        if any(k in header_lower for k in [
            # 英文关键词
            'method', 'material', 'procedure', 'experiment', 'experimental',
            'sampling', 'analysis', 'measurement', 'instrument', 'equipment',
            'protocol', 'technique', 'preparation',
            # 中文关键词
            '方法', '材料', '实验', '样品', '检测', '质量控制', '质控',
            '设备', '仪器', '采样', '分析方法', '测定', '试剂', 
            '操作', '步骤', '流程', '制备', '处理', '测试'
        ]) or re.match(r'^2\.', header_lower):  # 数字模式：2.x
            return 'Methods_Materials'
        
        # ===== Results（结果）=====
        if any(k in header_lower for k in [
            # 英文关键词
            'result', 'finding', 'data', 'table', 'figure', 'fig',
            'content', 'concentration', 'level', 'distribution', 
            'observation', 'outcome',
            # 中文关键词
            '结果', '数据', '含量', '浓度', '水平', '分布', 
            '检出', '测定结果', '测量', '观察', '表', '图'
        ]) or re.match(r'^3\.(?!\d)', header_lower):  # 数字模式：3.x（但不是3.x.x）
            return 'Results'
        
        # ===== Discussion（讨论）=====
        if any(k in header_lower for k in [
            # 英文关键词
            'discussion', 'interpretation', 'implication', 'analysis',
            'risk', 'exposure', 'assessment', 'evaluation', 'impact',
            'health', 'safety', 'hazard',
            # 中文关键词
            '讨论', '分析', '评价', '风险', '暴露', '影响', 
            '健康', '安全', '危害', '机制', '原因', '比较'
        ]) or re.match(r'^3\.\d+\.', header_lower):  # 数字模式：3.x.x
            return 'Discussion'
        
        # ===== Conclusion（结论）=====
        if any(k in header_lower for k in [
            'conclusion', 'summary', 'closing', 'outlook', 'perspective',
            '结论', '总结', '小结', '展望', '建议', '对策'
        ]) or re.match(r'^[45]\.', header_lower):  # 数字模式：4.x或5.x
            return 'Conclusion'
        
        # ===== References（参考文献）=====
        if any(k in header_lower for k in [
            'reference', 'bibliography', 'bibliographies', 'citation', 'literature',
            'literature cited', 'works cited',
            '参考文献', '文献', '引用'
        ]):
            return 'References'
        
        # ===== 文本特征匹配（辅助判断）=====
        # Methods特征
        if any(k in text_lower for k in [
            'we collected', '我们收集', 'we used', '我们使用',
            'sampling was', '采样', 'according to', '根据', 
            'were analyzed', '进行分析', 'measured by', '测定'
        ]):
            return 'Methods_Materials'
        
        # Results特征
        if any(k in text_lower for k in [
            'p<', 'p =', 'p value', 'p<0.', 'p =0.',
            'significant', '显著', 'was found', '发现', 
            'showed', '显示', 'indicated', '表明'
        ]):
            return 'Results'
        
        # ========== 第二层：LLM兜底（慢但准确）==========
        # 只有规则都不匹配时才调用LLM
        
        if llm is None:
            # 如果没有提供LLM，返回Other
            return 'Other'
        
        try:
            llm_call_count['count'] += 1
            print(f"   🤖 LLM推断 ({llm_call_count['count']}): {header[:40]}...")
            
            # 构建prompt
            prompt = f"""请判断以下学术论文章节属于哪个类型。

标题：{header}

内容前200字：
{text[:200]}

类型选项（只能从中选择一个）：
- Abstract: 摘要
- Introduction: 引言/背景
- Methods_Materials: 方法与材料/实验设计
- Results: 结果/数据/表格
- Discussion: 讨论/分析/评价
- Conclusion: 结论/总结
- References: 参考文献
- Other: 其他

要求：
1. 只回答类型的英文名称（如 "Methods_Materials"）
2. 不要添加任何解释或标点符号
3. 如果不确定，回答 "Other"

答案："""
            
            # 👇 关键修改：使用LangChain API
            # 方式1：使用invoke（推荐）
            response = llm.invoke(prompt)
            
            # 提取结果
            # response是AIMessage对象，需要取.content
            section_role = response.content.strip()
            
            # 验证返回值
            valid_sections = [
                'Abstract', 'Introduction', 'Methods_Materials', 
                'Results', 'Discussion', 'Conclusion', 'References', 'Other'
            ]
            
            if section_role in valid_sections:
                print(f"      ✅ LLM判断: {section_role}")
                return section_role
            else:
                # LLM返回了无效值，尝试模糊匹配
                section_lower = section_role.lower()
                for valid in valid_sections:
                    if valid.lower() in section_lower:
                        print(f"      ✅ LLM判断（修正）: {valid}")
                        return valid
                
                # 完全无法识别
                print(f"      ⚠️ LLM返回无效值: {section_role}，使用Other")
                return 'Other'
        
        except Exception as e:
            print(f"      ⚠️ LLM推断失败: {e}")
            import traceback
            traceback.print_exc()
            return 'Other'
    
    return infer