# 代码结构清理说明

## 清理背景

项目最初包含了重复的代码目录结构，导致代码组织不清晰，可能造成混淆和维护困难。本次清理旨在统一代码结构，确保所有组件遵循一致的包结构。

## 清理内容

### 移除的重复目录

以下内容已被移动到`/archive`目录下存档:

- `/src/core/` - 核心组件的旧版本
- `/src/util/` - 工具函数的旧版本
- `/src/distributed/` - 分布式组件的旧版本
- `/src/server/` - 服务器组件的旧版本
- `/src/cli.py` - 旧版命令行接口
- `/src/utils/` - 未使用的空目录

### 保留的目录结构

所有代码现在集中在`/src/task_planner/`目录下，遵循Python包的标准结构：

```
/src/task_planner/
├── __init__.py
├── cli.py                # 命令行入口点
├── core/                 # 核心功能
│   ├── context_management.py
│   ├── task_decomposition_system.py
│   ├── task_executor.py
│   ├── task_planner.py
│   └── tools/            # 核心工具模块
├── distributed/          # 分布式功能
├── server/               # 服务器组件
├── util/                 # 辅助工具
└── vendor/               # 第三方集成
    └── claude_client/    # Claude相关功能
        └── agent_tools/  # 包含Gemini集成等
```

### 入口点更新

- 更新了`setup.py`中的入口点，从`cli:main`改为`task_planner.cli:main`
- 将最新版本的`cli.py`复制到了`src/task_planner/cli.py`

## 清理依据

1. **测试分析**：通过分析`/tests/`目录，发现所有测试都是基于`task_planner.core`等包路径进行导入，没有任何测试使用`core`直接导入

2. **文件时间对比**：对比发现`src/task_planner/`下的文件是最新版本
   - `task_planner.py`: 33KB (旧) vs 55KB (新)
   - `task_executor.py`: 24KB (旧) vs 40KB (新)
   - `context_management.py`: 14KB (旧) vs 20KB (新)

3. **代码规范**：统一项目结构遵循Python包的最佳实践，便于维护和扩展

## 后续工作

1. **更新文档**：已更新README.md，反映最新的项目结构
2. **测试验证**：重新安装包后，命令行功能和现有测试应该全部正常工作

## 清理日期

清理完成日期: 2025-03-06
