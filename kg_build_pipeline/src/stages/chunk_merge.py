"""Chunk dedup within same filename (from 1_2_0_2 module5)."""
from __future__ import annotations

# chunk去重（可独立运行）
# -*- coding: utf-8 -*-
import hashlib
from typing import Dict, List, Optional, Any
from neo4j import Driver

class ChunkMerger:
    """精准的Chunk节点合并器 - 仅在同一 filename 内合并，不影响其他节点和关系"""
    
    def __init__(self, driver: Driver):
        self.driver = driver
    
    def merge_duplicate_chunks(self) -> Dict[str, int]:
        """合并重复的Chunk节点（仅合并filename相同的重复），保护其他所有数据"""
        stats = {"original_chunks": 0, "duplicate_groups": 0, "merged_chunks": 0, "final_chunks": 0}
        with self.driver.session() as session:
            stats["original_chunks"] = session.run("MATCH (c:Chunk) RETURN count(c) AS cnt").single()["cnt"]
            duplicate_groups = self._find_duplicate_groups(session)
            stats["duplicate_groups"] = len(duplicate_groups)
            if duplicate_groups:
                print(f"🔍 发现 {len(duplicate_groups)} 组重复Chunk（按 filename 分组）")
                for i, group in enumerate(duplicate_groups):
                    merged_count = self._merge_chunk_group(session, group, i+1)
                    stats["merged_chunks"] += merged_count
                self._rebuild_next_chunk_chain(session)  # 按 filename 分组重建链条
            stats["final_chunks"] = session.run("MATCH (c:Chunk) RETURN count(c) AS cnt").single()["cnt"]
        return stats
    
    def _find_duplicate_groups(self, session) -> List[List[Dict[str, Any]]]:
        """找出所有重复的Chunk组（限定：同一 filename 内部；基于 text 或 embedding）"""
        query = """
        MATCH (c:Chunk)
        WHERE c.filename IS NOT NULL AND c.filename <> ''
        WITH c.filename AS filename,
             c.text AS text,
             CASE WHEN c.embedding IS NOT NULL THEN c.embedding ELSE 'no_embedding' END AS embedding,
             collect({ id: elementId(c), index: coalesce(c.index, 999999), filename: c.filename }) AS chunks
        WHERE size(chunks) > 1
        RETURN filename, text, embedding, chunks
        ORDER BY size(chunks) DESC
        """
        result = session.run(query)
        duplicate_groups = []
        for rec in result:
            chunks = rec["chunks"]
            # 防御：再次确保组内 filename 一致
            fns = {x.get("filename") for x in chunks}
            if len(chunks) > 1 and len(fns) == 1 and list(fns)[0] is not None:
                duplicate_groups.append(chunks)
        return duplicate_groups
    
    def _merge_chunk_group(self, session, chunk_group: List[Dict[str, Any]], group_num: int) -> int:
        """合并一组重复的Chunk节点（默认同一 filename 组）"""
        if len(chunk_group) <= 1:
            return 0
        # 再保险：组内 filename 必须一致，不一致直接跳过
        fn_set = {c["filename"] for c in chunk_group}
        if len(fn_set) != 1:
            print(f"⚠️ 组{group_num}: 检测到混合 filename，跳过")
            return 0
        filename = next(iter(fn_set))
        # 按 index 排序，选最小 index 为保留
        chunk_group.sort(key=lambda x: x["index"])
        target_chunk = chunk_group[0]
        source_chunks = chunk_group[1:]
        print(f"   组{group_num} [file={filename}]: 保留index={target_chunk['index']}，合并{len(source_chunks)}个重复")
        for source_chunk in source_chunks:
            self._transfer_chunk_relationships(session, source_chunk["id"], target_chunk["id"])
        return len(source_chunks)
    
    def _transfer_chunk_relationships(self, session, source_id: str, target_id: str):
        """将源Chunk的所有关系转移到目标Chunk，然后删除源Chunk"""
        self._transfer_incoming_relations(session, source_id, target_id)
        self._transfer_outgoing_relations(session, source_id, target_id)
        session.run("MATCH (s:Chunk) WHERE elementId(s)=$sid DETACH DELETE s", sid=source_id)
    
    def _transfer_incoming_relations(self, session, source_id: str, target_id: str):
        incoming = session.run("""
            MATCH (source:Chunk) WHERE elementId(source)=$sid
            MATCH (target:Chunk) WHERE elementId(target)=$tid
            MATCH (other)-[r]->(source)
            WHERE other <> target
            RETURN elementId(other) AS other_id, type(r) AS rel_type, properties(r) AS rel_props
        """, sid=source_id, tid=target_id).data()
        for rel in incoming:
            session.run(f"""
                MATCH (o) WHERE elementId(o)=$oid
                MATCH (t:Chunk) WHERE elementId(t)=$tid
                MERGE (o)-[nr:{rel['rel_type']}]->(t)
                SET nr += $props
            """, oid=rel["other_id"], tid=target_id, props=rel["rel_props"])
        session.run("MATCH (s:Chunk) WHERE elementId(s)=$sid MATCH (o)-[r]->(s) DELETE r", sid=source_id)
    
    def _transfer_outgoing_relations(self, session, source_id: str, target_id: str):
        outgoing = session.run("""
            MATCH (source:Chunk) WHERE elementId(source)=$sid
            MATCH (target:Chunk) WHERE elementId(target)=$tid
            MATCH (source)-[r]->(other)
            WHERE other <> target
            RETURN elementId(other) AS other_id, type(r) AS rel_type, properties(r) AS rel_props
        """, sid=source_id, tid=target_id).data()
        for rel in outgoing:
            session.run(f"""
                MATCH (t:Chunk) WHERE elementId(t)=$tid
                MATCH (o) WHERE elementId(o)=$oid
                MERGE (t)-[nr:{rel['rel_type']}]->(o)
                SET nr += $props
            """, tid=target_id, oid=rel["other_id"], props=rel["rel_props"])
        session.run("MATCH (s:Chunk) WHERE elementId(s)=$sid MATCH (s)-[r]->(o) DELETE r", sid=source_id)
    
    def _rebuild_next_chunk_chain(self, session):
        """按 filename 分组重建 NEXT_CHUNK 链条（仅处理带 index 的 Chunk）"""
        # 删除所有 Chunk→Chunk 的 NEXT_CHUNK
        deleted = session.run("""
            MATCH (c1:Chunk)-[r:NEXT_CHUNK]->(c2:Chunk) 
            DELETE r 
            RETURN count(r) AS deleted
        """).single()["deleted"]
        if deleted > 0:
            print(f"   清理了 {deleted} 个旧的NEXT_CHUNK关系")
        # 按 filename 分组、按 index 排序重建
        created = session.run("""
            MATCH (c:Chunk)
            WHERE c.index IS NOT NULL AND c.filename IS NOT NULL AND c.filename <> ''
            WITH c.filename AS fn, c ORDER BY fn, c.index
            WITH fn, collect(c) AS chunks
            UNWIND range(0, size(chunks)-2) AS i
            WITH chunks[i] AS cur, chunks[i+1] AS nxt
            CREATE (cur)-[:NEXT_CHUNK]->(nxt)
            RETURN count(*) AS created
        """).single()["created"]
        print(f"   创建了 {created} 个新的NEXT_CHUNK关系（按 filename 分组）")
    
    def verify_merge_result(self) -> Dict[str, Any]:
        """验证合并结果 - 仅检查Chunk相关数据（按 filename 检查重复）"""
        with self.driver.session() as session:
            duplicate_check = session.run("""
                MATCH (c:Chunk)
                WHERE c.filename IS NOT NULL AND c.filename <> ''
                WITH c.filename AS fn, c.text AS text, count(*) AS cnt
                WHERE cnt > 1
                RETURN count(*) AS duplicate_groups
            """).single()["duplicate_groups"]
            chunk_stats = session.run("""
                MATCH (c:Chunk)
                WITH count(c) AS total_chunks
                OPTIONAL MATCH (c1:Chunk)-[r:NEXT_CHUNK]->(c2:Chunk)
                WITH total_chunks, count(r) AS next_relations
                OPTIONAL MATCH (c:Chunk) WHERE c.index IS NOT NULL
                RETURN total_chunks, next_relations, count(c) AS indexed_chunks
            """).single()
            chain_integrity = True
            if chunk_stats["indexed_chunks"] > 1:
                # 由于按 filename 分组重建，这里用分文件期望边数的宽松校验
                expected = session.run("""
                    MATCH (c:Chunk)
                    WHERE c.index IS NOT NULL AND c.filename IS NOT NULL AND c.filename <> ''
                    WITH c.filename AS fn, count(c) AS cnt
                    RETURN reduce(s=0, x IN collect(cnt) | s + CASE WHEN x>0 THEN x-1 ELSE 0 END) AS expected
                """).single()["expected"]
                actual = chunk_stats["next_relations"]
                chain_integrity = (actual >= expected)
            total_stats = session.run("""
                MATCH (n) WITH count(n) AS total_nodes
                MATCH ()-[r]->() WITH total_nodes, count(r) AS total_relations
                RETURN total_nodes, total_relations
            """).single()
            return {
                "chunk_count": chunk_stats["total_chunks"],
                "next_chunk_relations": chunk_stats["next_relations"],
                "indexed_chunks": chunk_stats["indexed_chunks"],
                "duplicate_groups_remaining": duplicate_check,
                "chain_complete": chain_integrity,
                "total_nodes": total_stats["total_nodes"],
                "total_relations": total_stats["total_relations"]
            }

# 主要使用函数
async def merge_chunks_after_extraction(neo4j_driver: Driver) -> bool:
    """在论文抽取完成后合并重复Chunk（仅同 filename 内部），不影响其他数据"""
    print("🔧 开始合并重复Chunk节点...")
    merger = ChunkMerger(neo4j_driver)
    try:
        stats = merger.merge_duplicate_chunks()
        print(f"📊 Chunk合并完成:")
        print(f"   原始Chunk: {stats['original_chunks']}")
        print(f"   重复组数: {stats['duplicate_groups']}")
        print(f"   合并节点: {stats['merged_chunks']}")
        print(f"   最终Chunk: {stats['final_chunks']}")
        rate = ((stats['original_chunks'] - stats['final_chunks']) / stats['original_chunks'] * 100) if stats['original_chunks'] else 0.0
        print(f"   压缩率: {rate:.1f}%")
        verification = merger.verify_merge_result()
        print(f"✅ 验证结果:")
        print(f"   剩余重复组: {verification['duplicate_groups_remaining']}")
        print(f"   NEXT_CHUNK链基本完整: {'是' if verification['chain_complete'] else '否'}")
        print(f"   数据库总节点: {verification['total_nodes']}")
        print(f"   数据库总关系: {verification['total_relations']}")
        return verification["chain_complete"] and verification["duplicate_groups_remaining"] == 0
    except Exception as e:
        print(f"❌ Chunk合并失败: {e}")
        import traceback; traceback.print_exc()
        return False

def cleanup_existing_chunk_duplicates(driver: Driver) -> Dict[str, Any]:
    """清理现有数据库中的重复Chunk - 安全模式（仅同 filename 内部合并）"""
    print("🧽 清理现有Chunk重复...")
    merger = ChunkMerger(driver)
    before = merger.verify_merge_result()
    print(f"清理前: {before['chunk_count']} 个Chunk，{before['duplicate_groups_remaining']} 组重复")
    merged = merger.merge_duplicate_chunks()
    after = merger.verify_merge_result()
    result = {
        "before": before, "merge_stats": merged, "after": after,
        "success": after["duplicate_groups_remaining"] == 0 and after["chain_complete"]
    }
    print(f"清理完成: {after['chunk_count']} 个Chunk，链条{'完整' if after['chain_complete'] else '不完整'}")
    return result


def run_chunk_merge(driver: Driver) -> Dict[str, Any]:
    """Merge duplicate Chunk nodes (same filename only)."""
    merger = ChunkMerger(driver)
    stats = merger.merge_duplicate_chunks()
    verification = merger.verify_merge_result()
    return {"merge": stats, "verification": verification}


if __name__ == "__main__":
    # 示例：按你现有环境获取 driver
    import utilities.return_llm_database
    manager = utilities.return_llm_database.DatabaseManager(remotedatebase=False)
    _, _, neo4j_driver = manager.get_components()
    success = cleanup_existing_chunk_duplicates(neo4j_driver)
