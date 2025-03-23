# AG2执行器简化重构设计

## 问题背景

当前AG2执行器在文件时间戳处理上存在几个关键问题：

1. 时间戳字典在传递过程中创建了新副本而非直接引用
2. 参数嵌套结构过于复杂，导致获取时间戳困难
3. 文件路径表示不一致，造成时间戳匹配失败
4. 缺乏统一的路径处理机制

## 简化设计方案

### 1. 核心原则

- **直接引用**: 所有工具共享同一个时间戳字典引用，不复制
- **统一路径**: 标准化文件路径处理，确保键一致性
- **简化参数**: 减少嵌套层级，简化参数传递
- **强化调试**: 添加清晰的日志和错误处理

### 2. 时间戳管理

```python
class AG2Executor:
    def __init__(self):
        # 单一中央时间戳字典
        self.file_timestamps = {}
        
        # 用于处理路径的辅助函数
        self.normalize_path = lambda p: str(Path(p).resolve())
        
    def update_timestamp(self, file_path):
        """更新文件时间戳，统一处理路径"""
        normalized_path = self.normalize_path(file_path)
        orig_path = str(file_path)
        
        # 记录当前时间
        current_time = time.time()
        self.file_timestamps[normalized_path] = current_time
        
        # 同时记录原始路径，确保不同表示形式能找到相同时间戳
        if normalized_path != orig_path:
            self.file_timestamps[orig_path] = current_time
            
    def verify_timestamp(self, file_path):
        """验证文件时间戳，用于编辑前检查"""
        normalized_path = self.normalize_path(file_path)
        orig_path = str(file_path)
        
        # 检查规范化路径
        if normalized_path in self.file_timestamps:
            last_time = self.file_timestamps[normalized_path]
            current_mtime = os.path.getmtime(normalized_path)
            
            if current_mtime > last_time:
                return False, "文件在上次读取后被修改"
            return True, ""
            
        # 检查原始路径
        if orig_path in self.file_timestamps:
            return self.verify_timestamp(orig_path)
            
        return False, "文件尚未被读取"
```

### 3. 工具注册简化

```python
def _register_tool(self, tool_instance):
    """向AG2注册工具，并注入时间戳字典引用"""
    executor = self  # 保存外部引用
    
    def tool_wrapper(params):
        """工具包装函数，确保时间戳字典引用一致"""
        try:
            # 确保参数格式一致
            if not isinstance(params, dict):
                params = {"args": params}
                
            # 添加上下文
            if "context" not in params:
                params["context"] = {}
                
            # 重要: 直接使用AG2执行器的时间戳字典引用
            params["context"]["timestamps"] = executor.file_timestamps
            
            # 添加调试信息
            print(f"[TOOL] 执行工具: {tool_instance.name}")
            print(f"[TOOL] 时间戳字典ID: {id(executor.file_timestamps)}")
            
            # 执行工具
            result = tool_instance.execute(params)
            return result
            
        except Exception as e:
            print(f"[ERROR] 工具执行失败: {str(e)}")
            raise
    
    # 注册工具函数
    register_function(
        tool_wrapper,
        name=tool_instance.name,
        description=tool_instance.description
    )
```

### 4. 文件读取工具简化

```python
class FileReadTool(BaseTool):
    def execute(self, params):
        """简化后的文件读取实现"""
        try:
            # 获取文件路径
            file_path = params.get("file_path")
            if not file_path:
                return {"success": False, "error": "缺少文件路径参数"}
                
            # 获取时间戳字典
            timestamps = params.get("context", {}).get("timestamps", {})
            
            # 读取文件
            with open(file_path, 'r') as f:
                content = f.read()
                
            # 更新时间戳 - 使用绝对路径和原始路径
            abs_path = str(Path(file_path).resolve())
            timestamps[abs_path] = time.time()
            timestamps[file_path] = timestamps[abs_path]  # 同时记录原始路径
            
            return {
                "success": True, 
                "content": content,
                "file_path": file_path
            }
            
        except Exception as e:
            return {"success": False, "error": f"读取文件失败: {str(e)}"}
```

### 5. 文件编辑工具简化

```python
class FileEditTool(BaseTool):
    def execute(self, params):
        """简化后的文件编辑实现"""
        try:
            # 获取参数
            file_path = params.get("file_path")
            old_string = params.get("old_string")
            new_string = params.get("new_string")
            
            # 基本参数验证
            if not all([file_path, old_string is not None, new_string is not None]):
                return {"success": False, "error": "缺少必要参数"}
                
            # 获取时间戳字典
            timestamps = params.get("context", {}).get("timestamps", {})
            if not timestamps:
                return {"success": False, "error": "缺少时间戳字典"}
                
            # 验证文件是否已读取
            abs_path = str(Path(file_path).resolve())
            
            # 检查时间戳 - 查找任何匹配的路径形式
            timestamp_found = False
            for path_key in [abs_path, file_path]:
                if path_key in timestamps:
                    timestamp_found = True
                    # 检查文件是否被修改
                    if os.path.getmtime(file_path) > timestamps[path_key]:
                        return {"success": False, "error": "文件在读取后被修改"}
                    break
                    
            if not timestamp_found:
                return {"success": False, "error": "文件尚未被读取"}
                
            # 读取并修改文件
            with open(file_path, 'r') as f:
                content = f.read()
                
            # 检查唯一性
            if old_string not in content:
                return {"success": False, "error": "要替换的内容不存在"}
                
            if content.count(old_string) > 1:
                return {"success": False, "error": "找到多处匹配，请提供更多上下文"}
                
            # 替换内容
            new_content = content.replace(old_string, new_string)
            
            # 写入文件
            with open(file_path, 'w') as f:
                f.write(new_content)
                
            # 更新时间戳
            timestamps[abs_path] = time.time()
            timestamps[file_path] = timestamps[abs_path]
            
            return {"success": True, "message": "文件编辑成功"}
            
        except Exception as e:
            return {"success": False, "error": f"编辑文件失败: {str(e)}"}
```

## 实现与测试

### 简单测试用例

```python
def test_timestamp_sharing():
    """测试时间戳共享和路径处理"""
    # 创建执行器
    executor = AG2Executor()
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
        temp.write("测试内容\n")
        temp_path = temp.name
        
    try:
        # 注册工具 - 使用同一个时间戳字典
        read_tool = FileReadTool()
        edit_tool = FileEditTool()
        
        # 读取文件
        read_result = read_tool.execute({
            "file_path": temp_path,
            "context": {"timestamps": executor.file_timestamps}
        })
        print(f"读取结果: {read_result}")
        print(f"时间戳字典: {executor.file_timestamps}")
        
        # 编辑文件
        edit_result = edit_tool.execute({
            "file_path": temp_path,
            "old_string": "测试内容",
            "new_string": "修改后的内容",
            "context": {"timestamps": executor.file_timestamps}
        })
        print(f"编辑结果: {edit_result}")
        
        # 验证修改
        with open(temp_path, 'r') as f:
            content = f.read()
        print(f"文件内容: {content}")
        
        assert "修改后的内容" in content, "文件内容未被修改"
        
    finally:
        # 清理临时文件
        os.unlink(temp_path)
```

## 迁移策略

1. 修改`AG2Executor`类，确保时间戳字典作为单一引用
2. 更新工具注册机制，注入时间戳字典引用
3. 简化工具实现，统一路径处理
4. 编写单元测试验证时间戳共享和路径处理
5. 增加详细日志，帮助排查问题

## 对比原设计的优势

1. **简单明了**: 仅修改必要部分，不引入复杂结构
2. **直接共享**: 时间戳字典直接共享引用，避免副本问题
3. **路径一致**: 统一路径处理，确保匹配成功
4. **易于理解**: 逻辑清晰，容易掌握
5. **改动最小**: 对现有代码结构改动小

## 注意事项

1. 确保所有工具访问同一个时间戳字典引用
2. 统一路径处理函数，解决规范化问题
3. 加强调试日志，记录关键点
4. 添加路径匹配的容错机制
5. 维护向后兼容性，确保现有功能不受影响