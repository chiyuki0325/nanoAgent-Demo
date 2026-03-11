def recall(self, query, top_k=5, score_threshold=0.35):
    """
    针对用户输入，从向量库提取事实(Facts)，从实体库提取画像(Entities)
    """
    # 1. 生成查询向量
    query_vector = self._get_embedding(query)

    # 2. 检索向量事实 (Facts)
    # 这里的 score_threshold 可以过滤掉相关性太低的噪音
    search_results = self.qdrant.search(
        collection_name=self.collection_name,
        query_vector=query_vector,
        limit=top_k,
        score_threshold=score_threshold
    )

    # 提取 Facts 文本并去重（如果有重复）
    retrieved_facts = []
    for hit in search_results:
        fact_text = hit.payload.get("text", "")
        # 你可以在这里加上时间戳格式化，比如 [2026.3.9] xxx
        retrieved_facts.append(f"- {fact_text} (Relevance: {hit.score:.2f})")

    # 3. 匹配实体画像 (Entities)
    # 遍历实体库，寻找 Query 中提到的实体（支持别名匹配）
    matched_entities = []
    for name, data in self.entity_registry.items():
        # 如果 Query 里提到了实体名或其任何一个别名
        if name in query or any(alias in query for alias in data.get("aliases", [])):
            attr_str = ", ".join([f"{k}: {v}" for k, v in data['attributes'].items()])
            matched_entities.append(f"[{name}] 类型: {data['type']}, 当前状态: {{{attr_str}}}")

    # 4. 组装最终呈现给 LLM 的上下文 (Memory Block)
    if not retrieved_facts and not matched_entities:
        return "No relevant memories found."

    memory_block = "### 相关记忆片段 (Relevant Memories):\n"
    memory_block += "\n".join(retrieved_facts) if retrieved_facts else "无相关事实数据。"
    
    memory_block += "\n\n### 相关实体画像 (Entity Context):\n"
    memory_block += "\n".join(matched_entities) if matched_entities else "未识别到相关实体。"

    return memory_block



"""
实际系统设计时，组装记忆部分应存在于上下文装配器中
"""