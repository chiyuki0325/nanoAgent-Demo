import os
import json
import subprocess
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL")
)

# --- 1. 扩展工具定义 ---
tools = [
    # ... 原有的 execute_bash, read_file, write_file 保持不变 ...
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Execute a bash command",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    # 新增 spawn 功能
    {
        "type": "function",
        "function": {
            "name": "spawn_subagent",
            "description": "Create a specialized subagent to handle a subtask independently.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The specific task for the subagent"},
                    "system_prompt": {"type": "string", "description": "Instructions or persona for the subagent"}
                },
                "required": ["task"],
            },
        },
    },
]

# --- 2. 实现 Spawn 逻辑 ---

def spawn_subagent(task, system_prompt="You are a helpful subagent."):
    """
    核心创新：递归调用 run_agent。
    这会开启一个全新的上下文空间，子代理的中间过程不会污染主代理。
    """
    print(f"\n[Spawn] >>> Starting Subagent for task: {task[:50]}...")
    # 递归调用主循环，注意可以限制子代理的 max_iterations 防止无限递归
    result = run_agent(task, system_prompt=system_prompt, max_iterations=3, is_subagent=True)
    print(f"[Spawn] <<< Subagent completed.\n")
    return f"Subagent Result: {result}"

def execute_bash(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr

def read_file(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception as e:
        return str(e)

def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)
    return f"Wrote to {path}"

# 映射函数名
functions = {
    "execute_bash": execute_bash, 
    "read_file": read_file, 
    "write_file": write_file,
    "spawn_subagent": spawn_subagent # 注册到函数字典
}

# --- 3. 修改 run_agent 以支持递归和不同 persona ---

def run_agent(user_message, system_prompt="You are a helpful assistant. Be concise.", max_iterations=5, is_subagent=False):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    
    prefix = "  " if is_subagent else "" # 打印时区分层级

    for i in range(max_iterations):
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            tools=tools,
        )
        message = response.choices[0].message
        messages.append(message)
        
        if not message.tool_calls:
            return message.content
        
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            print(f"{prefix}[Tool] {name}({args})")
            
            if name not in functions:
                result = f"Error: Unknown tool '{name}'"
            else:
                # 动态调用（如果是 spawn_subagent，它会递归回 run_agent）
                result = functions[name](**args)
            
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
            
    return "Max iterations reached"

if __name__ == "__main__":
    import sys
    # 示例任务：让它分析一个文件并写总结，强制它使用 subagent
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
           "请帮我创建一个 hello.py，然后派一个子代理专门负责检查代码里的语法错误并运行它。"
    
    print("--- Parent Agent Starting ---")
    final_output = run_agent(task)
    print("\n--- Final Result ---")
    print(final_output)