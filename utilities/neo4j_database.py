from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore

def clear_neo4j_database(graph_store):
    """
    清空Neo4j数据库中的所有数据

    Args:
        graph_store: Neo4j图存储对象
    """
    try:
        # 执行清空操作
        with graph_store._driver.session() as session:
            # 删除所有节点和关系
            session.run("MATCH (n) DETACH DELETE n")
            print("✅ Neo4j数据库已清空")
    except Exception as e:
        print(f"⚠️ 清空Neo4j数据库失败: {e}")

def setup_neo4j_store(username, password, url, clear_existing=True):
    """
    设置Neo4j图存储

    Args:
        username: Neo4j用户名
        password: Neo4j密码
        url: Neo4j连接URL
        clear_existing: 是否清空现有数据

    Returns:
        Neo4jPropertyGraphStore: 图存储对象
    """
    try:
        graph_store = Neo4jPropertyGraphStore(
            username=username,
            password=password,
            url=url
        )

        print("✅ Neo4j连接成功")

        # 清空现有数据
        if clear_existing:
            clear_neo4j_database(graph_store)

        return graph_store

    except Exception as e:
        print(f"❌ Neo4j连接失败: {e}")
        raise