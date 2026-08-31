# schema_loader.py
import json
from typing import Any, Dict, List

class SchemaLoader:
    def __init__(self, base_path: str = r"C:\data\schema\EAS"):
        self.base_path = base_path
        self.entities_path = f"{self.base_path}\\entity.json"
        self.relations_path = f"{self.base_path}\\relation.json"
        self.potential_schema_path = f"{self.base_path}\\potential_schema.json"

        self._entities_data: Dict[str, Any] = {}
        self._relations_data: Dict[str, Any] = {}
        self._potential_schema_data: Dict[str, Any] = {}

        self._entities: List[Dict] = []
        self._relations: List[Dict] = []
        self._potential_schema: List[Dict] = []

    def _load_json(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"错误: 找不到文件 {path}")
            raise
        except json.JSONDecodeError as e:
            print(f"错误: 无法解析 JSON 文件 {path}: {e}")
            raise
        except Exception as e:
            print(f"加载文件 {path} 时发生未知错误: {e}")
            raise

    def load_entities_data(self) -> Dict[str, Any]:
        if not self._entities_data:
            self._entities_data = self._load_json(self.entities_path)
        return self._entities_data

    def load_relations_data(self) -> Dict[str, Any]:
        if not self._relations_data:
            self._relations_data = self._load_json(self.relations_path)
        return self._relations_data

    def load_potential_schema_data(self) -> Dict[str, Any]:
        if not self._potential_schema_data:
            self._potential_schema_data = self._load_json(self.potential_schema_path)
        return self._potential_schema_data

    def load_entities(self) -> List[Dict]:
        if not self._entities:
            data = self.load_entities_data()
            self._entities = data.get("entities", [])
        return self._entities

    def load_relations(self) -> List[Dict]:
        if not self._relations:
            data = self.load_relations_data()
            self._relations = data.get("relations", [])
        return self._relations

    def load_potential_schema(self) -> List[Dict]:
        if not self._potential_schema:
            data = self.load_potential_schema_data()
            self._potential_schema = data.get("potential_schema", [])
        return self._potential_schema

    def load_all(self):
        """
        一次性加载所有 Schema 数据。
        
        Returns:
            tuple[list[dict], list[dict], list[dict]]:
                一个包含三个元素的元组:
                (entities_list, relations_list, potential_schema_list)
                
        Example:
            entities, relations, potential_schemas = loader.load_all()
        """
        # 调用各自的加载方法，这些方法会处理缓存
        entities_list = self.load_entities() 
        relations_list = self.load_relations()
        potential_schema_list = self.load_potential_schema()
        
        # 返回一个包含三个列表的元组
        return entities_list, relations_list, potential_schema_list

# ... （SchemaLoader 类的其他部分保持不变） ...

    @property
    def entities(self) -> List[Dict]:
        return self.load_entities()

    @property
    def relations(self) -> List[Dict]:
        return self.load_relations()

    @property
    def potential_schema(self) -> List[Dict]:
        return self.load_potential_schema()