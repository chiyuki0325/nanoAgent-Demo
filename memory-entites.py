def extract_entities(self, chat_logs):
        """
        提取实体并更新现有的实体库
        """
        # 1. 使用 Few-shot 引导 LLM 输出结构化 JSON
        prompt = f"""
你是一个实体提取专家。请从对话中提取实体（人物、系统、组织等），并输出为 JSON 格式。
如果实体已有别名或特定属性，请一并提取。

### 示例 1：
输入："斩风千雪 2026.3.9: 救命，这选课系统又崩了。"
输出：
{{
  "entities": [
    {{
      "name": "斩风千雪",
      "aliases": ["千雪"],
      "attributes": {{"identity": "用户", "status": "遇到选课问题"}}
    }},
    {{
      "name": "选课系统",
      "aliases": ["系统"],
      "attributes": {{"status": "崩溃", "issue": "性能瓶颈"}}
    }}
  ]
}}

### 任务：
输入对话：
{chat_logs}

输出要求：严格 JSON 格式，不要有任何解释文字。
"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }, # 强制 JSON 输出
            temperature=0.1
        )

        new_entities = json.loads(response.choices[0].message.content).get("entities", [])

        # 2. 实体库更新/合并逻辑
        for ent in new_entities:
            name = ent["name"]
            if name not in self.entity_registry:
                # 新增实体
                self.entity_registry[name] = {
                    "aliases": set(ent.get("aliases", [])),
                    "attributes": ent.get("attributes", {})
                }
            else:
                # 更新旧实体：合并别名，覆盖/新增属性
                self.entity_registry[name]["aliases"].update(ent.get("aliases", []))
                self.entity_registry[name]["attributes"].update(ent.get("attributes", {}))
        
        return f"Updated {len(new_entities)} entities in registry."

def get_entity_context(self, query):
    """
    辅助函数：根据查询寻找相关的实体画像
    """
    # 这里可以使用简单的关键词匹配，或者用向量检索实体的 'name' 和 'aliases'
    related_info = []
    for name, data in self.entity_registry.items():
        if name in query or any(alias in query for alias in data["aliases"]):
            info = f"Entity: {name} ({data['type']}), Attributes: {data['attributes']}"
            related_info.append(info)
    return related_info



"""
这里只是简单demo，实际进行设计时会采用知识图谱等技术，确保连贯和可靠性
"""