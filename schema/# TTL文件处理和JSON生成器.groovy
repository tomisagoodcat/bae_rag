# TTL文件处理和JSON生成器
import json
import pandas as pd
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, URIRef
from rdflib.namespace import XSD
from collections import defaultdict
import re

class TTLToJSONConverter:
    def __init__(self, ttl_file_path):
        """
        初始化转换器
        """
        self.ttl_file = ttl_file_path
        self.graph = Graph()
        self.extracted_properties = []
        self.entities = []
        self.relations = []
        self.potential_schemas = []
        
        # 定义命名空间
        self.WHU = Namespace("http://example.org/whu#")
        self.MP = Namespace("http://purl.org/mp#")
        self.PPLAN = Namespace("http://purl.org/net/p-plan#")
        
        # 加载TTL文件
        self.load_ttl()
    
    def load_ttl(self):
        """加载TTL文件"""
        try:
            self.graph.parse(self.ttl_file, format='turtle')
            print(f"✅ 成功加载TTL文件: {self.ttl_file}")
        except Exception as e:
            print(f"❌ 加载TTL文件失败: {e}")
            raise
    
    def extract_properties_from_restrictions(self):
        """
        从类约束中提取对象属性并生成独立的属性定义
        """
        print("🔄 开始提取嵌套的对象属性...")
        
        for cls in self.graph.subjects(RDF.type, OWL.Class):
            for restriction in self.graph.objects(cls, RDFS.subClassOf):
                if (restriction, RDF.type, OWL.Restriction) in self.graph:
                    prop = self.graph.value(restriction, OWL.onProperty)
                    range_val = self.graph.value(restriction, OWL.someValuesFrom)
                    
                    if prop and range_val and not self._is_datatype_range(range_val):
                        # 检查是否已经是独立定义的属性
                        if not (prop, RDF.type, OWL.ObjectProperty) in self.graph:
                            # 提取注释和prompt
                            comments_en = list(self.graph.objects(restriction, RDFS.comment))
                            prompts = list(self.graph.objects(restriction, self.WHU.prompt))
                            
                            property_info = {
                                'uri': str(prop),
                                'domain': str(cls),
                                'range': str(range_val),
                                'comments_en': [str(c) for c in comments_en if c.language == 'en' or not c.language],
                                'comments_zh': [str(c) for c in comments_en if c.language == 'zh'],
                                'prompts': [str(p) for p in prompts]
                            }
                            
                            self.extracted_properties.append(property_info)
        
        print(f"✅ 提取了 {len(self.extracted_properties)} 个嵌套的对象属性")
    
    def _is_datatype_range(self, range_uri):
        """判断是否为数据类型范围"""
        if not range_uri:
            return False
        
        range_str = str(range_uri)
        datatype_patterns = [
            'XMLSchema#string', 'XMLSchema#float', 'XMLSchema#integer', 
            'XMLSchema#date', 'XMLSchema#boolean', 'XMLSchema#anyURI',
            'xsd:string', 'xsd:float', 'xsd:integer', 'xsd:date'
        ]
        
        return any(pattern in range_str for pattern in datatype_patterns)
    
    def _get_short_name(self, uri):
        """获取URI的短名称"""
        uri_str = str(uri)
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        return uri_str
    
    def _get_label(self, uri):
        """获取资源的标签"""
        label = self.graph.value(uri, RDFS.label)
        return str(label) if label else self._get_short_name(uri)
    
    def _get_description(self, uri):
        """获取资源的描述"""
        # 尝试获取prompt作为描述
        prompt = self.graph.value(uri, self.WHU.prompt)
        if prompt:
            return str(prompt)
        
        # 如果没有prompt，尝试获取英文注释
        for comment in self.graph.objects(uri, RDFS.comment):
            if comment.language == 'en' or not comment.language:
                return str(comment)
        
        return ""
    
    def generate_entities_json(self):
        """生成entities.json"""
        print("🔄 生成entities.json...")
        
        try:
            # 处理所有类
            for cls in self.graph.subjects(RDF.type, OWL.Class):
                entity = {
                    "label": self._get_short_name(cls).upper(),
                    "description": self._get_description(cls),
                    "properties": self._extract_data_properties(cls)
                }
                self.entities.append(entity)
            
            print(f"✅ 生成了 {len(self.entities)} 个实体")
            
        except Exception as e:
            print(f"❌ 生成entities.json失败: {e}")
            raise
    
    def _extract_data_properties(self, cls):
        """提取类的数据属性"""
        properties = []
        
        # 独立定义的数据属性
        for prop in self.graph.subjects(RDF.type, OWL.DatatypeProperty):
            domain = self.graph.value(prop, RDFS.domain)
            if domain == cls:
                properties.append(self._create_property_info(prop))
        
        # 从约束中提取的数据属性
        for restriction in self.graph.objects(cls, RDFS.subClassOf):
            if (restriction, RDF.type, OWL.Restriction) in self.graph:
                prop = self.graph.value(restriction, OWL.onProperty)
                range_val = self.graph.value(restriction, OWL.someValuesFrom)
                
                if prop and range_val and self._is_datatype_range(range_val):
                    properties.append(self._create_property_info(prop, restriction))
        
        return properties
    
    def _create_property_info(self, prop, restriction=None):
        """创建属性信息字典"""
        range_val = None
        description = ""
        
        if restriction:
            range_val = self.graph.value(restriction, OWL.someValuesFrom)
            # 从约束中获取描述
            for comment in self.graph.objects(restriction, RDFS.comment):
                if comment.language == 'en' or not comment.language:
                    description = str(comment)
                    break
            if not description:
                prompt = self.graph.value(restriction, self.WHU.prompt)
                if prompt:
                    description = str(prompt)
        else:
            range_val = self.graph.value(prop, RDFS.range)
            description = self._get_description(prop)
        
        return {
            "name": self._get_short_name(prop).upper(),
            "type": self._map_datatype_to_type(range_val),
            "description": description
        }
    
    def _map_datatype_to_type(self, datatype_uri):
        """将数据类型URI映射到简单类型"""
        if not datatype_uri:
            return "STRING"
        
        datatype_str = str(datatype_uri).lower()
        
        if 'float' in datatype_str or 'double' in datatype_str or 'decimal' in datatype_str:
            return "FLOAT"
        elif 'int' in datatype_str:
            return "INTEGER"
        elif 'bool' in datatype_str:
            return "BOOLEAN"
        elif 'date' in datatype_str:
            return "DATE"
        else:
            return "STRING"
    
    def generate_relations_json(self):
        """生成relations.json"""
        print("🔄 生成relations.json...")
        
        try:
            # 处理独立定义的对象属性
            for prop in self.graph.subjects(RDF.type, OWL.ObjectProperty):
                relation = {
                    "label": self._get_short_name(prop).upper(),
                    "description": self._get_description(prop),
                    "properties": []
                }
                self.relations.append(relation)
            
            # 处理从约束中提取的对象属性
            for extracted_prop in self.extracted_properties:
                relation = {
                    "label": self._get_short_name(extracted_prop['uri']).upper(),
                    "description": self._get_extracted_description(extracted_prop),
                    "properties": []
                }
                self.relations.append(relation)
            
            print(f"✅ 生成了 {len(self.relations)} 个关系")
            
        except Exception as e:
            print(f"❌ 生成relations.json失败: {e}")
            raise
    
    def _get_extracted_description(self, extracted_prop):
        """获取提取属性的描述"""
        if extracted_prop['prompts']:
            return extracted_prop['prompts'][0]
        elif extracted_prop['comments_en']:
            return extracted_prop['comments_en'][0]
        return ""
    
    def generate_potential_schemas_json(self):
        """生成potential_schemas.json"""
        print("🔄 生成potential_schemas.json...")
        
        try:
            # 收集所有实体和关系的标签
            entity_labels = {entity['label'] for entity in self.entities}
            relation_labels = {relation['label'] for relation in self.relations}
            
            schemas = []
            
            # 从独立定义的对象属性生成三元组
            schemas.extend(self._extract_schemas_from_properties(entity_labels, relation_labels))
            
            # 从提取的属性生成三元组
            schemas.extend(self._extract_schemas_from_extracted(entity_labels, relation_labels))
            
            # 去重
            self.potential_schemas = self._deduplicate_schemas(schemas)
            
            print(f"✅ 生成了 {len(self.potential_schemas)} 个潜在模式")
            
        except Exception as e:
            print(f"❌ 生成potential_schemas.json失败: {e}")
            raise
    
    def _extract_schemas_from_properties(self, entity_labels, relation_labels):
        """从独立定义的对象属性提取模式"""
        schemas = []
        for prop in self.graph.subjects(RDF.type, OWL.ObjectProperty):
            domain = self.graph.value(prop, RDFS.domain)
            range_val = self.graph.value(prop, RDFS.range)
            
            if domain and range_val:
                schema = self._create_schema_if_valid(
                    domain, prop, range_val, entity_labels, relation_labels
                )
                if schema:
                    schemas.append(schema)
        return schemas
    
    def _extract_schemas_from_extracted(self, entity_labels, relation_labels):
        """从提取的属性生成模式"""
        schemas = []
        for extracted_prop in self.extracted_properties:
            schema = self._create_schema_if_valid(
                extracted_prop['domain'], 
                extracted_prop['uri'], 
                extracted_prop['range'],
                entity_labels, 
                relation_labels
            )
            if schema:
                schemas.append(schema)
        return schemas
    
    def _create_schema_if_valid(self, domain, prop, range_val, entity_labels, relation_labels):
        """创建有效的模式三元组"""
        domain_label = self._get_short_name(domain).upper()
        range_label = self._get_short_name(range_val).upper()
        relation_label = self._get_short_name(prop).upper()
        
        # 验证实体和关系是否存在
        if (domain_label in entity_labels and 
            range_label in entity_labels and 
            relation_label in relation_labels):
            
            return {
                "head": domain_label,
                "relation": relation_label,
                "tail": range_label
            }
        return None
    
    def _deduplicate_schemas(self, schemas):
        """去重模式列表"""
        seen = set()
        unique_schemas = []
        
        for schema in schemas:
            schema_tuple = (schema['head'], schema['relation'], schema['tail'])
            if schema_tuple not in seen:
                seen.add(schema_tuple)
                unique_schemas.append(schema)
        
        return unique_schemas
    
    def save_files(self, output_dir="./"):
        """保存所有输出文件"""
        print("💾 保存输出文件...")
        
        try:
            # 保存JSON文件
            json_files = [
                ('entities.json', self.entities),
                ('relations.json', self.relations), 
                ('potential_schemas.json', self.potential_schemas)
            ]
            
            for filename, data in json_files:
                with open(f"{output_dir}{filename}", 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 保存TTL文件
            self.generate_extracted_ttl(f"{output_dir}extracted_properties.ttl")
            self.generate_processed_ttl(f"{output_dir}processed_ontology.ttl")
            
            print("✅ 所有文件已保存")
            
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
            raise
    
    def generate_processed_ttl(self, output_file="processed_ontology.ttl"):
        """生成完整的处理后TTL文件"""
        print("🔄 生成完整的处理后TTL文件...")
        
        try:
            # 创建新的图用于输出
            output_graph = Graph()
            
            # 复制所有命名空间前缀
            for prefix, namespace in self.graph.namespaces():
                output_graph.bind(prefix, namespace)
            
            # 1. 复制所有非约束相关的三元组
            self._copy_base_triples(output_graph)
            
            # 2. 添加提取的独立对象属性
            self._add_extracted_properties(output_graph)
            
            # 3. 重构类定义（移除已提取的约束）
            self._reconstruct_classes(output_graph)
            
            # 序列化并保存
            output_graph.serialize(destination=output_file, format='turtle')
            print(f"✅ 完整处理后TTL文件已保存: {output_file}")
            
        except Exception as e:
            print(f"❌ 生成TTL文件失败: {e}")
            raise

    def _copy_base_triples(self, output_graph):
        """复制基础三元组（排除类约束）"""
        for s, p, o in self.graph:
            # 跳过类的subClassOf约束，其他都复制
            if not (p == RDFS.subClassOf and (o, RDF.type, OWL.Restriction) in self.graph):
                output_graph.add((s, p, o))

    def _add_extracted_properties(self, output_graph):
        """添加提取的独立对象属性"""
        for prop_info in self.extracted_properties:
            prop_uri = URIRef(prop_info['uri'])
            domain_uri = URIRef(prop_info['domain'])
            range_uri = URIRef(prop_info['range'])
            
            # 添加属性定义
            output_graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
            output_graph.add((prop_uri, RDFS.domain, domain_uri))
            output_graph.add((prop_uri, RDFS.range, range_uri))
            
            # 添加标签
            label = self._get_short_name(prop_info['uri'])
            output_graph.add((prop_uri, RDFS.label, Literal(label, lang='en')))
            
            # 添加注释
            for comment in prop_info['comments_en']:
                output_graph.add((prop_uri, RDFS.comment, Literal(comment, lang='en')))
            for comment in prop_info['comments_zh']:
                output_graph.add((prop_uri, RDFS.comment, Literal(comment, lang='zh')))
            
            # 添加prompt
            for prompt in prop_info['prompts']:
                output_graph.add((prop_uri, self.WHU.prompt, Literal(prompt, lang='en')))

    def _reconstruct_classes(self, output_graph):
        """重构类定义，移除已提取的对象属性约束"""
        extracted_props = {prop['uri'] for prop in self.extracted_properties}
        
        for cls in self.graph.subjects(RDF.type, OWL.Class):
            for restriction in self.graph.objects(cls, RDFS.subClassOf):
                if (restriction, RDF.type, OWL.Restriction) in self.graph:
                    prop = self.graph.value(restriction, OWL.onProperty)
                    range_val = self.graph.value(restriction, OWL.someValuesFrom)
                    
                    # 如果这个属性已经被提取，则不再添加约束
                    if str(prop) in extracted_props:
                        # 移除这个约束的subClassOf关系
                        output_graph.remove((cls, RDFS.subClassOf, restriction))
                        # 移除约束相关的所有三元组
                        for s, p, o in self.graph.triples((restriction, None, None)):
                            output_graph.remove((s, p, o))

    def generate_extracted_ttl(self, output_file="extracted_properties.ttl"):
        """生成仅包含提取属性的TTL文件"""
        print("🔄 生成提取的属性TTL文件...")
        
        try:
            extract_graph = Graph()
            
            # 绑定常用命名空间
            prefixes = {
                'owl': 'http://www.w3.org/2002/07/owl#',
                'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
                'whu': 'http://example.org/whu#'
            }
            
            for prefix, uri in prefixes.items():
                extract_graph.bind(prefix, uri)
            
            # 添加提取的属性
            self._add_extracted_properties(extract_graph)
            
            # 序列化保存
            extract_graph.serialize(destination=output_file, format='turtle')
            print(f"✅ 提取的属性TTL文件已保存: {output_file}")
            
        except Exception as e:
            print(f"❌ 生成提取属性TTL文件失败: {e}")
            raise
    
    def run_conversion(self):
        """运行完整的转换流程"""
        print("🚀 开始TTL到JSON转换流程...")
        
        try:
            # 1. 提取嵌套属性
            self.extract_properties_from_restrictions()
            
            # 2. 生成JSON文件
            self.generate_entities_json()
            self.generate_relations_json() 
            self.generate_potential_schemas_json()
            
            # 3. 保存所有文件
            self.save_files()
            
            # 4. 显示统计信息
            self.print_statistics()
            
            print("🎉 转换完成！")
            
        except Exception as e:
            print(f"❌ 转换流程失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def print_statistics(self):
        """打印统计信息"""
        print("\n📊 转换统计:")
        print(f"   - 提取的嵌套对象属性: {len(self.extracted_properties)}")
        print(f"   - 生成的实体: {len(self.entities)}")
        print(f"   - 生成的关系: {len(self.relations)}")
        print(f"   - 生成的潜在模式: {len(self.potential_schemas)}")
        
        print(f"\n📁 输出文件:")
        print(f"   - entities.json")
        print(f"   - relations.json") 
        print(f"   - potential_schemas.json")
        print(f"   - extracted_properties.ttl (仅提取的属性)")
        print(f"   - processed_ontology.ttl (完整处理后的本体)")
        
        # 显示示例
        if self.entities:
            print(f"\n💡 实体示例:")
            for entity in self.entities[:2]:
                props_count = len(entity['properties'])
                print(f"   - {entity['label']}: {props_count} 个属性")
        
        if self.relations:
            print(f"\n🔗 关系示例:")
            for relation in self.relations[:2]:
                print(f"   - {relation['label']}")
        
        if self.potential_schemas:
            print(f"\n📋 模式示例:")
            for schema in self.potential_schemas[:2]:
                print(f"   - {schema['head']} → {schema['relation']} → {schema['tail']}")

def main():
    """主函数"""
    ttl_file_path = r"C:\Users\tom\OneDrive\LUCK\luck grpahrag\code\PaperExtract\schema\ttl\class.ttl"  # 修改为您的TTL文件路径
    
    try:
        converter = TTLToJSONConverter(ttl_file_path)
        converter.run_conversion()
        
    except FileNotFoundError:
        print(f"❌ 找不到TTL文件: {ttl_file_path}")
        print("请确认文件路径正确")
    except Exception as e:
        print(f"❌ 转换过程中出现错误: {e}")

# 执行主函数
 
# 执行主函数
if __name__ == "__main__":
    main()