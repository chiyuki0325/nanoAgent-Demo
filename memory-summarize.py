def summarize(self, entities, chat_logs):
    """
    通过 Few-shot 示例引导 LLM 提取原子事实
    """
    system_prompt = f"""
你是一个专业的记忆提取助手。你的任务是从原始聊天记录中提取出独立的、客观的“原子事实（Atomic Facts）”。

### 提取准则：
1. 粒度拆分：将复杂的句子拆解为单一的事实。
2. 实体关联：明确事实的主体（谁、什么、何时）。请使用明确的主名称代指实体。
3. 状态记录：记录聊天隐含的系统状态、地理位置或时间节点的变化。

### 示例 1：
输入：
"董慧敏 2026.3.1 10:00: 刚才在一食堂二楼发现新开了个拉面档，味道不错"
"董慧敏 2026.3.1 12:00: 不行啊，这排队的人也太多了！"
输出：
- [2026.3.1 10:00] 一食堂二楼新开设了拉面档口。
- [2026.3.1 10:00] 董慧敏认为该拉面档口味道不错。
- [2026.3.1 12:00] 该拉面档口排队人数较多。

### 示例 2：
输入：
"斩风千雪 2026.3.9 12:10: 救命……选课开始都都十分钟了，系统还是提示我“培养计划不存在”，然后把我踢下线了。"
输出：
- [2026.3.9 12:00] 选课开始。
- [2026.3.9 12:10] 选课系统处于不稳定状态。
- [2026.3.9 12:10] 选课系统在用户补选时会报错提示“培养计划不存在”。
- [2026.3.9 12:10] 报错后，选课系统会强制用户下线（踢出登录）。
- [2026.3.9 12:10] 斩风千雪在尝试补选时遭遇了上述系统故障。
"""
    
    user_prompt = """
### 待处理任务：
存在的实体：
{entities}

输入对话记录：
{chat_logs}

请开始提取：
"""
    
    # 调用 LLM（这里建议设一个较低的 temperature 以保证稳定性）
    response = self.client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}],
        temperature=0.1 
    )
    
    # 分条解析
    return _parse_atomic_facts(response.choices[0].message.content)

def _parse_atomic_facts(self, llm_output):
    """
    解析 LLM 返回的原子事实列表
    """
    atomic_facts = []
    
    if not llm_output:
        return atomic_facts
    
    # 按行分割
    lines = llm_output.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        # 跳过空行
        if not line:
            continue
            
        # 匹配以 "- " 或 "• " 开头的事实条目
        if line.startswith('- ') or line.startswith('• '):
            fact = line[2:].strip()  # 去掉前缀
            
            # 提取时间戳（如果存在）
            timestamp = None
            if fact.startswith('[') and ']' in fact:
                time_end = fact.find(']')
                timestamp = fact[1:time_end].strip()
                fact_content = fact[time_end+1:].strip()
            else:
                fact_content = fact
            
            atomic_facts.append({
                'timestamp': timestamp,
                'fact': fact_content,
                'raw': line
            })
        
        # 也支持数字编号格式，如 "1. " 或 "1、"
        elif line and (line[0].isdigit() and ('. ' in line[:4] or '、' in line[:4])):
            # 移除数字编号
            if '. ' in line[:4]:
                fact = line.split('. ', 1)[1]
            elif '、' in line[:4]:
                fact = line.split('、', 1)[1]
            else:
                fact = line
                
            # 同样尝试提取时间戳
            timestamp = None
            if fact.startswith('[') and ']' in fact:
                time_end = fact.find(']')
                timestamp = fact[1:time_end].strip()
                fact_content = fact[time_end+1:].strip()
            else:
                fact_content = fact
            
            atomic_facts.append({
                'timestamp': timestamp,
                'fact': fact_content,
                'raw': line
            })
    
    # 如果上面都没有匹配到，但内容不为空，说明可能返回格式不规范
    if not atomic_facts and llm_output.strip():
        # 尝试将整个输出作为一个事实（保底方案）
        atomic_facts.append({
            'timestamp': None,
            'fact': llm_output.strip(),
            'raw': llm_output.strip()
        })
    
    return atomic_facts