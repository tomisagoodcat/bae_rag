# Notebook Cell 10 快速修复指南

## 问题
torch DLL错误导致无法初始化DatabaseManager

## 解决方案

### 修改Cell 10的代码

将以下代码：
```python
# ==============
# 初始化组件
# ==============
r = utilities.return_llm_database.DatabaseManager()
llm, embed_model, neo4j_driver = r.get_components()
```

**替换为：**

```python
# ==============
# 初始化组件
# ==============
# 注意：如果遇到torch DLL错误，使用skip_embedding=True参数
try:
    r = utilities.return_llm_database.DatabaseManager()
    llm, embed_model, neo4j_driver = r.get_components()
except (OSError, ImportError) as e:
    if "torch" in str(e).lower() or "dll" in str(e).lower():
        print(f"Warning: torch DLL问题，跳过embedding初始化: {e}")
        print("使用skip_embedding=True参数...")
        r = utilities.return_llm_database.DatabaseManager(skip_embedding=True)
        llm, neo4j_driver = r.get_components_without_embedding()
        embed_model = None
        print("✓ 已获取llm和neo4j_driver（embed_model=None）")
        print("提示: 如果需要embed_model，可以稍后手动创建或修复torch问题")
    else:
        raise

# 如果embed_model为None，尝试使用静态方法创建（用于HybridCypherRetriever）
if embed_model is None:
    print("Warning: embed_model为None，尝试使用静态方法创建...")
    try:
        embed_model = utilities.return_llm_database.DatabaseManager.get_embedding(type="neo4j")
        print("✓ 成功创建embed_model")
    except Exception as e:
        print(f"Error: 无法创建embed_model: {e}")
        print("提示: 需要修复torch DLL问题才能使用HybridCypherRetriever")
        # 如果仍然失败，embed_model将为None，HybridCypherRetriever可能无法使用
```

## 说明

1. **自动错误处理**: 代码会自动检测torch DLL错误，并使用`skip_embedding=True`参数
2. **延迟初始化**: 如果embed_model为None，会尝试使用静态方法创建
3. **兼容性**: 如果torch问题未修复，至少可以获取llm和neo4j_driver

## 测试

运行修改后的Cell 10，应该可以看到：
- ✓ 已获取llm和neo4j_driver（即使有警告）
- 如果成功创建embed_model，会显示"✓ 成功创建embed_model"

## 如果仍然失败

如果embed_model仍然无法创建，需要修复torch DLL问题：
1. 安装Visual C++ Redistributable
2. 重新安装torch（CPU版本）

详见 `TORCH_DLL_FIX_GUIDE.md`















