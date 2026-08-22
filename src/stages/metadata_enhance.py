"""DC metadata and relation enhancement (from 1_2_0_2 module2)."""
from __future__ import annotations

# ==================== 模块2: 元数据更新与关系增强 ====================

def update_metadata_batch(neo4j_driver, filename: str, dc_metadata: dict) -> bool:
    """
    批量更新Chunk/Entity/Relation的元数据（增强版 - 含from_section）
    
    功能：
    1. 为Chunk/Entity/Relation添加DC元数据
    2. 为所有节点和关系添加from_section属性（来自section_role）
    
    原理：
    - Chunk: from_section = section_role（如果section_role存在）
    - Entity: from_section = 关联Chunk的from_section
    - Relation: from_section = 关联Chunk的from_section
    """
    try:
        source_doc = filename.replace('.md', '')
        
        params = {
            'filename': filename,
            'source_doc': source_doc,
            'dc_title': dc_metadata.get('dc_title', source_doc),
            'dc_author': dc_metadata.get('dc_author', 'Unknown'),
            'dc_publisher': dc_metadata.get('dc_publisher', 'Unknown'),
            'dc_creator': dc_metadata.get('dc_creator', 'Unknown'),
            'dcterms_issued': dc_metadata.get('dcterms_issued', 'Unknown'),
            'dcterms_identifier': dc_metadata.get('dcterms_identifier', f'local:{source_doc}')
        }
        
        with neo4j_driver.session() as session:
            # ========== 步骤1：更新Chunk节点（添加from_section）==========
            session.run("""
                MATCH (chunk:Chunk)
                WHERE chunk.filename = $filename
                  AND chunk.dc_title IS NULL
                SET chunk.filename = $filename,
                    chunk.source_doc = $source_doc,
                    chunk.dc_title = $dc_title,
                    chunk.dc_author = $dc_author,
                    chunk.dc_publisher = $dc_publisher,
                    chunk.dc_creator = $dc_creator,
                    chunk.dcterms_issued = $dcterms_issued,
                    chunk.dcterms_identifier = $dcterms_identifier,
                    chunk.from_section = coalesce(chunk.section_role, chunk.from_section, 'Other'),
                    chunk.processed_at = datetime()
            """, **params)
            
            # ========== 步骤2：更新Entity节点（继承from_section）==========
            session.run("""
                MATCH (chunk:Chunk)-[:FROM_CHUNK]-(entity)
                WHERE chunk.filename = $filename
                  AND entity.dc_title IS NULL
                SET entity.dc_title = $dc_title,
                    entity.dc_author = $dc_author,
                    entity.dc_publisher = $dc_publisher,
                    entity.dc_creator = $dc_creator,
                    entity.dcterms_issued = $dcterms_issued,
                    entity.dcterms_identifier = $dcterms_identifier,
                    entity.source_doc = $source_doc,
                    entity.from_section = chunk.from_section
            """, **params)
            
            # ========== 步骤3：更新Relation关系（继承from_section）==========
            session.run("""
                MATCH (chunk:Chunk)-[:FROM_CHUNK]-(n1)-[r]-(n2)
                WHERE chunk.filename = $filename
                  AND type(r) <> 'FROM_CHUNK'
                  AND r.dc_title IS NULL
                SET r.dc_title = $dc_title,
                    r.dc_author = $dc_author,
                    r.dc_publisher = $dc_publisher,
                    r.dc_creator = $dc_creator,
                    r.dcterms_issued = $dcterms_issued,
                    r.dcterms_identifier = $dcterms_identifier,
                    r.source_doc = $source_doc,
                    r.from_section = chunk.from_section
            """, **params)
            
            print(f"✅ 元数据更新完成: {filename}")
            return True
            
    except Exception as e:
        print(f"❌ 元数据更新失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def enhance_relations(neo4j_driver, filename: str, dc_metadata: dict, llm) -> int:
    """
    为关系和节点增强属性（完整版）
    
    功能：
    1. 为Relation添加 WHU_HASORIGINALTEXT, WHU_HASNAME, llm_weight
    2. 为Node添加 llm_weight（如果缺失）
    
    原理：
    - 优先使用LLM在KG抽取时已提取的属性
    - 对于缺失的属性，使用规则或默认值补充
    """
    try:
        with neo4j_driver.session() as session:
            # ========== 步骤1：增强Relation属性 ==========
            result = session.run("""
                MATCH (chunk:Chunk)-[:FROM_CHUNK]-(n1)-[r]-(n2)
                WHERE chunk.filename = $filename
                  AND type(r) <> 'FROM_CHUNK'
                  AND r.WHU_HASORIGINALTEXT IS NULL
                RETURN id(r) as rel_id, 
                       type(r) as rel_type,
                       n1.WHU_HASNAME as source_name,
                       n1.WHU_HASORIGINALTEXT as source_text, 
                       n2.WHU_HASNAME as target_name,
                       n2.WHU_HASORIGINALTEXT as target_text,
                       chunk.text as chunk_text,
                       r.WHU_HASNAME as existing_name,
                       r.llm_weight as existing_weight
                LIMIT 100
            """, filename=filename)
            
            rels = list(result)
            if not rels:
                print(f"   ℹ️  所有关系已有完整属性")
            
            enhanced_rels = 0
            
            for rel in rels:
                try:
                    chunk_text = rel['chunk_text'] or ''
                    rel_type = rel['rel_type']
                    source_name = rel['source_name'] or ''
                    target_name = rel['target_name'] or ''
                    
                    # ===== 提取 WHU_HASORIGINALTEXT =====
                    # 策略：在chunk_text中找到包含两个实体的句子
                    sentences = chunk_text.replace('。', '.').split('.')
                    original_text = ''
                    
                    for sent in sentences:
                        sent_lower = sent.lower()
                        # 检查句子是否同时包含source和target的关键词
                        if (source_name.lower() in sent_lower and 
                            target_name.lower() in sent_lower):
                            original_text = sent.strip()[:300]
                            break
                    
                    # 如果没找到，使用chunk前200字符
                    if not original_text:
                        original_text = chunk_text[:200].strip() + "..."
                    
                    # ===== 生成 WHU_HASNAME =====
                    # 优先使用LLM已提取的
                    if rel['existing_name']:
                        whu_hasname = rel['existing_name']
                    else:
                        # 否则，基于关系类型生成
                        whu_hasname = rel_type.replace('_', ' ').lower()
                    
                    # ===== 评估 llm_weight =====
                    # 优先使用LLM已提取的
                    if rel['existing_weight'] is not None:
                        llm_weight = float(rel['existing_weight'])
                    else:
                        # 否则，基于文本特征评估
                        llm_weight = 0.5  # 默认中等权重
                        
                        text_lower = original_text.lower()
                        
                        # 高权重关键词（强因果、统计显著）
                        if any(k in text_lower for k in [
                            'significant', 'p<', 'p =', 'p<0.', 'p<0.0',
                            '显著', 'cause', 'lead to', 'result in', 
                            '导致', '产生', 'directly', '直接'
                        ]):
                            llm_weight = 0.85
                        
                        # 中等权重关键词（明确关联）
                        elif any(k in text_lower for k in [
                            'associated', 'correlated', 'related', 'linked',
                            '相关', '关联', 'indicate', '表明', 'showed', '显示'
                        ]):
                            llm_weight = 0.7
                        
                        # 低权重关键词（推测、可能）
                        elif any(k in text_lower for k in [
                            'may', 'might', 'could', 'possibly', 'suggest',
                            '可能', '暗示', 'unclear', '不清楚'
                        ]):
                            llm_weight = 0.4
                    
                    # ===== 更新关系属性 =====
                    session.run("""
                        MATCH ()-[r]->() 
                        WHERE id(r) = $rel_id
                        SET r.WHU_HASORIGINALTEXT = $original_text,
                            r.WHU_HASNAME = $whu_hasname,
                            r.llm_weight = $llm_weight,
                            r.dc_identifier = $dc_identifier
                    """, 
                        rel_id=rel['rel_id'],
                        original_text=original_text,
                        whu_hasname=whu_hasname,
                        llm_weight=llm_weight,
                        dc_identifier=dc_metadata.get('dcterms_identifier', '')
                    )
                    
                    enhanced_rels += 1
                    
                except Exception as e:
                    print(f"      ⚠️ 关系增强失败: {e}")
                    continue
            
            if enhanced_rels > 0:
                print(f"   ✅ 增强了 {enhanced_rels} 个关系属性")
            
            # ========== 步骤2：增强Node的llm_weight（如果缺失）==========
            result = session.run("""
                MATCH (chunk:Chunk)-[:FROM_CHUNK]-(node)
                WHERE chunk.filename = $filename
                  AND node.llm_weight IS NULL
                  AND node.WHU_HASNAME IS NOT NULL
                RETURN id(node) as node_id,
                       labels(node)[0] as label,
                       node.WHU_HASNAME as name,
                       node.WHU_HASORIGINALTEXT as original_text
                LIMIT 100
            """, filename=filename)
            
            nodes = list(result)
            enhanced_nodes = 0
            
            for node_rec in nodes:
                try:
                    label = node_rec['label']
                    name = node_rec['name'] or ''
                    original_text = node_rec['original_text'] or ''
                    
                    # 基于节点类型和文本特征评估权重
                    llm_weight = 0.6  # 默认
                    
                    # 核心实体类型（高权重）
                    if label in ['whu_Pollutant', 'mp_Claim', 'whu_DataSet', 
                                'whu_EnvironmentFeature']:
                        llm_weight = 0.85
                    
                    # 重要支持实体
                    elif label in ['whu_Specimen', 'whu_Computational_Experiment',
                                  'whu_BioChemical_Experiment', 'whu_Bio_chemical_Experiment']:
                        llm_weight = 0.75
                    
                    # 标准实体
                    elif label in ['whu_Instrument', 'whu_Method', 'mp_Method', 'mp_Statement']:
                        llm_weight = 0.6
                    
                    # 次要实体
                    else:
                        llm_weight = 0.5
                    
                    # 根据文本特征微调
                    text_lower = (name + ' ' + original_text).lower()
                    
                    # 强调词 → 提升权重
                    if any(k in text_lower for k in [
                        'significant', 'critical', 'primary', 'main', 'key',
                        '主要', '关键', '重要', '核心'
                    ]):
                        llm_weight = min(llm_weight + 0.1, 1.0)
                    
                    # 更新节点权重
                    session.run("""
                        MATCH (node)
                        WHERE id(node) = $node_id
                        SET node.llm_weight = $llm_weight
                    """, 
                        node_id=node_rec['node_id'],
                        llm_weight=llm_weight
                    )
                    
                    enhanced_nodes += 1
                    
                except Exception as e:
                    continue
            
            if enhanced_nodes > 0:
                print(f"   ✅ 增强了 {enhanced_nodes} 个节点权重")
            
            return enhanced_rels + enhanced_nodes
            
    except Exception as e:
        print(f"❌ 属性增强失败: {e}")
        import traceback
        traceback.print_exc()
        return 0