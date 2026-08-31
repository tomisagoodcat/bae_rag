# 尝试导入ChatOpenAI，如果失败则设为None（可能因为torch DLL问题）
try:
    from langchain_openai import ChatOpenAI
except (ImportError, OSError) as e:
    print(f"Warning: 无法导入ChatOpenAI ({e})，某些功能可能受限")
    ChatOpenAI = None

from neo4j import GraphDatabase
#from llama_index.llms.openai import OpenAI
#from llama_index.embeddings.openai import OpenAIEmbedding
# 尝试导入HuggingFaceEmbedding，如果失败则设为None
try:
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
except (ImportError, OSError) as e:
    print(f"Warning: 无法导入HuggingFaceEmbedding ({e})，将使用SentenceTransformerEmbeddings作为替代")
    HuggingFaceEmbedding = None

from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
try:
    from sentence_transformers import SentenceTransformer
except (ImportError, OSError) as e:
    print(f"Warning: 无法导入SentenceTransformer ({e})")
    SentenceTransformer = None

try:
    import torch
except (ImportError, OSError) as e:
    print(f"Warning: 无法导入torch ({e})，某些功能可能受限")
    torch = None

class DatabaseManager:
    def __init__(self, remotedatebase=False, embed_model="neo4j", skip_embedding=False):
        """初始化数据库管理器
        
        Args:
            remotedatebase: 是否使用远程数据库
            embed_model: embedding模型类型 ("neo4j" 或 "huggingface")
            skip_embedding: 如果为True，跳过embedding初始化（用于torch DLL问题时的临时解决方案）
        """
        self.remotedatebase = remotedatebase
        self.embed_model_type = embed_model
        
        # 初始化组件
        self.llm = self._init_llm()
        if skip_embedding:
            print("Warning: 跳过embedding初始化（skip_embedding=True）")
            self.embed_model = None
        else:
            try:
                self.embed_model = self._init_embedding()
            except (ImportError, OSError) as e:
                print(f"Warning: embedding初始化失败 ({e})，设置为None")
                print("提示: 如果只需要driver和llm，可以使用skip_embedding=True参数")
                self.embed_model = None
        self.neo4j_driver = self._init_database()
    
    def _init_llm(self):
        """初始化LLM"""
        return OpenAILLM(
            model_name="deepseek-chat",
            model_params={
                "max_tokens": 8000,
                "temperature": 0.1,
                "top_p": 0.9,
                "frequency_penalty": 0.1,
            },
            api_key="YOUR_DEEPSEEK_API_KEY",
            base_url='https://api.deepseek.com/beta'
        )
    
    def _init_embedding(self):
        """初始化嵌入模型"""
        if self.embed_model_type == "neo4j":
            return SentenceTransformerEmbeddings(model="maidalun1020/bce-embedding-base_v1")
        else:
            if HuggingFaceEmbedding is not None:
                return HuggingFaceEmbedding(model_name="maidalun1020/bce-embedding-base_v1")
            else:
                # 如果HuggingFaceEmbedding不可用，回退到SentenceTransformerEmbeddings
                print("Warning: HuggingFaceEmbedding不可用，使用SentenceTransformerEmbeddings作为替代")
                return SentenceTransformerEmbeddings(model="maidalun1020/bce-embedding-base_v1")
    
    def _init_database(self):
        """初始化数据库连接"""
        if self.remotedatebase:
            NEO4J_URI = "neo4j+s://1b6c92d6.databases.neo4j.io"
            NEO4J_USERNAME = "neo4j"
            NEO4J_PASSWORD = "YOUR_NEO4J_PASSWORD"
            return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        else:
            config = {
                'url': "bolt://localhost:7687",
                'username': "neo4j",
                'password': "tomis1cat"
            }
            return GraphDatabase.driver(config['url'], auth=(config['username'], config['password']))
    
    def clear_database(self):
        """清空Neo4j数据库"""
        if not self.neo4j_driver:
            print("错误: 数据库驱动为空")
            return False
        
        try:
            with self.neo4j_driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
                print("数据库已清空")
            return True
        except Exception as e:
            print(f"清空数据库失败: {e}")
            return False
    
    def get_components(self):
        """返回所有组件"""
        return self.llm, self.embed_model, self.neo4j_driver
    
    def get_components_without_embedding(self):
        """返回组件（不包括embedding），用于torch不可用的情况"""
        return self.llm, self.neo4j_driver
    
    def close(self):
        """关闭数据库连接"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
            print("数据库连接已关闭")

# 为了向后兼容，保留原有函数
    def return_llm_database(remotedatebase=False, embed_model="neo4j"):
        """向后兼容的函数"""
        manager = DatabaseManager(remotedatebase, embed_model)
        return manager.get_components()

 
        

    # ========= 新增：静态方法，直接返回 neo4j driver =========
    @staticmethod
    def get_neo4j_driver(remotedatebase=False):
            """
            静态初始化并返回 Neo4j 驱动。
            用法：driver = DatabaseManager.get_neo4j_driver(remotedatebase=True/False)
            """
            if remotedatebase:
                NEO4J_URI = "neo4j+s://1b6c92d6.databases.neo4j.io"
                NEO4J_USERNAME = "neo4j"
                NEO4J_PASSWORD = "YOUR_NEO4J_PASSWORD"
                return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
            else:
                config = {
                    'url': "bolt://localhost:7687",
                    'username': "neo4j",
                    'password': "tomis1cat"
                }
                return GraphDatabase.driver(config['url'], auth=(config['username'], config['password']))
        # ========= 新增：静态方法，直接返回 llm模型 =========
    @staticmethod
    def get_llm(type="deepseek"):
            """
            静态初始化并返回 Neo4j 驱动。
            用法：driver = DatabaseManager.get_neo4j_driver(remotedatebase=True/False)
            """


            if type=="deepseek":               
                return OpenAILLM(
                    model_name="deepseek-chat",
                    model_params={
                        "max_tokens": 8000,
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "frequency_penalty": 0.1,
                    },
                    api_key="YOUR_DEEPSEEK_API_KEY",
                    base_url='https://api.deepseek.com/v1'
                )
            else:
                return None
              
        # ========= 新增结束 =========
    # ========= 新增：静态方法，直接返回 embedding=========
    @staticmethod
    def get_embedding(type="neo4j"):
        """
        静态初始化并返回 embedding。
        用法：type="neo4j" 默认为neo4j 检索使用的embedding驱动方式，否则为标准huggingface embedding
        """
        try:
            if type == "neo4j":
                return SentenceTransformerEmbeddings(model="maidalun1020/bce-embedding-base_v1")
            elif type == "huggingface":
                if HuggingFaceEmbedding is not None:
                    return HuggingFaceEmbedding(model_name="maidalun1020/bce-embedding-base_v1")
                else:
                    # 如果HuggingFaceEmbedding不可用，回退到SentenceTransformerEmbeddings
                    print("Warning: HuggingFaceEmbedding不可用，使用SentenceTransformerEmbeddings作为替代")
                    return SentenceTransformerEmbeddings(model="maidalun1020/bce-embedding-base_v1")
            else:
                return None
        except (ImportError, OSError) as e:
            print(f"Error: 无法初始化embedding模型 ({e})")
            print("这可能是因为torch DLL加载问题。请检查环境或使用其他embedding方法。")
            raise
        # ========= 新增结束 =========

from openai import OpenAI

# DeepSeek 客户端
deepseek_client = OpenAI(
    api_key="your-deepseek-api-key",
    base_url="https://api.deepseek.com"
)

# OpenAI 客户端（可选）
openai_client = OpenAI(
    api_key="your-openai-api-key"
)

def chat(messages, model="deepseek-chat", temperature=0, config={}):
    """
    与 DeepSeek API 兼容的 chat 函数。
    参数与 OpenAI 的版本完全一致。
    """
    import openai

    openai.api_key = "YOUR_DEEPSEEK_API_KEY"
    openai.base_url = "https://api.deepseek.com/beta"
    response = openai.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages,
        **config,
    )
    return response.choices[0].message.content
