# Task Planner 系统重构设计 v2

## 1. 当前问题

在 Task Planner 重构 v1 实施后，我们发现主要存在以下问题：

1. **AI 输出处理机制问题**：
   - 当 Claude 未能创建实际文件时，系统会自动创建 JSON 占位符文件
   - 这导致任务链中的后续任务引用无效的 JSON 文件，而非预期的内容文件
   - 通过检查代码，问题出现在 TaskExecutor.execute_subtask 方法中（187-214行）的逻辑
   
2. **错误处理逻辑不明确**：
   - 当任务预期输出文件未被创建时，系统应明确报告错误
   - 当前实现掩盖了问题，通过创建 JSON 占位符使任务表面上"成功"
   - 这使得调试变得困难，因为表面上看所有任务都"成功"了

3. **提示词不够明确**：
   - 对 Claude 的指令中没有足够强调实际文件创建的重要性
   - 当前提示词仅说明"请将所有生成的结果保存到以下文件"，但未强调这是必须的
   - 没有明确告知 Claude 文件创建失败会导致整个任务失败

## 2. 设计原则和重构目标

任务规划与执行的设计原则是：
- 规划者负责生成任务规划和基于执行结果动态调整规划
- 执行者基于任务说明执行并生成实际文件（而不是返回文件内容供系统创建）
- 任务结果描述（JSON）中包含生成文件的路径信息
- 任务间通过文件路径进行上下文传递，而不是文件内容

基于此原则，我们的重构目标是：

1. **修改文件处理逻辑**：
   - 移除自动创建 JSON 占位符的逻辑
   - 当预期文件未被创建时，明确报告任务失败
   - 保留执行者对文件创建情况的验证和记录功能

2. **增强任务说明有效性**：
   - 在规划者生成任务定义时，确保明确包含 output_files 字段
   - 在执行者的任务提示词中，强调文件创建的必要性和重要性
   - 明确指出文件创建失败将导致任务失败

3. **改进错误反馈**：
   - 提供更明确的错误信息，指出具体哪些文件未被创建
   - 确保错误传递到上层，使规划者能根据失败情况调整计划

## 3. 具体修改内容

### 3.1 修改 TaskExecutor 类中的文件处理逻辑

1. **修改 execute_subtask 方法中的文件验证逻辑**：
   
   ```python
   # 修改前（187-214行）
   if not os.path.exists(result_file_path):
       # 若没有生成，则手动创建
       try:
           # 生成结果JSON
           result_json = {
               "task_id": subtask_id,
               "success": basic_result.get('success', False),
               "result": {
                   "summary": basic_result.get('result', {}).get('summary', '任务执行完成'),
                   "details": basic_result.get('result', {}).get('details', '')
               }
           }
           
           # 添加工件和下一步信息
           if 'artifacts' in basic_result:
               result_json['artifacts'] = basic_result['artifacts']
           
           if 'next_steps' in basic_result:
               result_json['next_steps'] = basic_result['next_steps']
               
           # 保存到文件
           with open(result_file_path, 'w', encoding='utf-8') as f:
               json.dump(result_json, f, ensure_ascii=False, indent=2)
               
           logger.info(f"为子任务 {subtask_id} 生成结果文件: {result_file_path}")
   
   # 修改后
   if 'output_files' in subtask and isinstance(subtask['output_files'], dict):
       missing_files = []
       for output_type, output_path in subtask['output_files'].items():
           if not os.path.isabs(output_path) and self.context_manager and self.context_manager.context_dir:
               output_path = os.path.join(self.context_manager.context_dir, output_path)
               
           if not os.path.exists(output_path):
               missing_files.append(f"{output_type}: {output_path}")
       
       if missing_files:
           error_msg = f"任务执行失败：AI未能创建预期的输出文件。缺失的文件：\n" + "\n".join(missing_files)
           self.logger.error(error_msg)
           return {
               "success": False,
               "error": error_msg,
               "task_id": subtask.get("id", "unknown"),
               "result": {"details": error_msg}
           }
   ```

2. **修改错误结果文件处理逻辑（248-282行）**：
   - 保留任务失败时的错误记录和提示，但不创建替代文件
   - 调整成仅保留日志记录，不再创建JSON文件

### 3.2 增强 _prepare_context_aware_prompt 方法

修改提示词生成逻辑（322-343行），明确强调文件创建的重要性：

```python
# 添加输出文件路径
if 'output_files' in subtask and isinstance(subtask['output_files'], dict):
    prompt_parts.append("\n## 输出文件要求")
    prompt_parts.append("你必须创建以下具体文件：")

    for output_type, output_path in subtask['output_files'].items():
        if output_type == 'main_result':
            prompt_parts.append(f"- 主要结果: {output_path}")
        else:
            prompt_parts.append(f"- {output_type}: {output_path}")

    # 强调文件创建的重要性
    prompt_parts.append("\n重要提示：")
    prompt_parts.append("1. 你必须实际创建这些文件，而不是仅描述它们应该包含什么内容")
    prompt_parts.append("2. 任务的成功完全取决于这些文件是否被成功创建")
    prompt_parts.append("3. 如果任何一个文件未被创建，整个任务将被视为失败")
    prompt_parts.append("4. 在回复中，请明确列出你已创建的每个文件的完整路径")
    prompt_parts.append("5. 如果无法创建任何文件，请明确指出并解释原因")
```

### 3.3 增强规划者的任务生成逻辑

1. **分析现有代码**:
   - 从代码分析可知，系统提示词(183-196行)已经要求包含output_files字段
   - 但_build_breakdown_prompt方法(1030-1068行)中没有明确提到output_files
   - _normalize_subtasks方法(970-1003行)没有验证output_files字段

2. **修改 TaskPlanner._build_breakdown_prompt 方法**:
   ```python
   # 在1063行后添加对输出文件的明确要求
   - 详细指令
   - 输入文件(input_files)：指定任务所需的输入文件路径
   - 输出文件(output_files)：明确指定任务必须生成的所有文件路径，包括结果文件和其他产物
   - 预期输出
   ```

3. **更新 TaskPlanner._normalize_subtasks 方法**:
   ```python
   # 在998行后添加对output_files的验证
   # 确保有输出文件定义
   if 'output_files' not in subtask or not isinstance(subtask['output_files'], dict):
       subtask['output_files'] = {'main_result': f"results/task_{i+1}/result.json"}
       
   # 确保main_result存在
   if 'main_result' not in subtask['output_files']:
       subtask['output_files']['main_result'] = f"results/task_{i+1}/result.json"
   ```

## 4. 实现进度

### 4.1 已完成的代码修改

✅ 所有计划的代码修改已全部完成：

1. **TaskExecutor修改**:
   - 已移除创建JSON占位符的逻辑，改为直接验证所有预期输出文件
   - 已更新错误处理部分，不再创建占位符JSON文件，而是创建日志文件
   - 已增强提示词生成，添加强调文件创建重要性的部分

2. **TaskPlanner修改**:
   - 已修改任务分解提示词，明确包含对output_files的要求
   - 已更新任务规范化逻辑，确保所有任务都有正确的output_files定义

### 4.2 已完成的测试文件

✅ 已创建详细的测试用例验证修改的功能：

1. **[test_file_validation.py]**:
   - 测试文件验证逻辑能否正确识别和报告缺失文件
   - 测试系统不再创建JSON占位符文件
   - 测试任务失败时的错误处理是否正确

2. **[test_prompt_generation.py]**:
   - 测试提示词中是否包含文件创建重要性的强调
   - 测试不同类型输出文件的提示词生成
   - 测试复杂上下文情况下的提示词生成

3. **[test_task_normalization.py]**:
   - 测试任务规范化过程确保output_files字段存在
   - 测试不同情况下的main_result文件路径添加
   - 测试任务分解提示词包含对output_files的说明

4. **[test_file_dependencies.py]**:
   - 测试任务链中前置任务文件缺失时的行为
   - 测试部分文件依赖存在的处理方式
   - 测试所有文件依赖都存在时的成功流程

### 4.3 测试结果

✅ 所有单元测试均已通过:

```
============================= test session starts ==============================
platform linux -- Python 3.12.0, pytest-8.3.3, pluggy-1.5.0
rootdir: /home/wangbo/document/wangbo/task_planner
configfile: pyproject.toml
plugins: mock-3.14.0, asyncio-0.23.6, anyio-3.7.1
asyncio: mode=Mode.STRICT
collecting ... collected 13 items

tests/test_file_validation.py::TestFileValidation::test_file_validation_logic PASSED [  7%]
tests/test_file_validation.py::TestFileValidation::test_no_placeholder_creation PASSED [ 15%]
tests/test_file_validation.py::TestFileValidation::test_error_handling_no_placeholder PASSED [ 23%]
tests/test_prompt_generation.py::TestPromptGeneration::test_prompt_includes_file_creation_emphasis PASSED [ 30%]
tests/test_prompt_generation.py::TestPromptGeneration::test_prompt_format_with_different_output_types PASSED [ 38%]
tests/test_prompt_generation.py::TestPromptGeneration::test_prompt_with_complex_context PASSED [ 46%]
tests/test_task_normalization.py::TestTaskNormalization::test_subtask_normalization_ensures_output_files PASSED [ 53%]
tests/test_task_normalization.py::TestTaskNormalization::test_normalize_multiple_subtasks PASSED [ 61%]
tests/test_task_normalization.py::TestTaskNormalization::test_task_breakdown_includes_output_files PASSED [ 69%]
tests/test_task_normalization.py::TestTaskNormalization::test_build_breakdown_prompt_includes_output_files PASSED [ 76%]
tests/test_file_dependencies.py::TestFileDependencies::test_task_chain_with_missing_files PASSED [ 84%]
tests/test_file_dependencies.py::TestFileDependencies::test_partial_file_dependencies PASSED [ 92%]
tests/test_file_dependencies.py::TestFileDependencies::test_successful_file_dependencies PASSED [100%]

============================== 13 passed in 0.45s ==============================
```

测试结果表明:
- 文件验证逻辑能正确识别缺失文件并返回适当的错误
- 任务执行器不再创建占位符文件，而是适当地报告错误
- 提示词生成功能已增强，明确强调文件创建的重要性
- 任务规范化确保所有任务都有合适的output_files定义
- 文件依赖的处理逻辑正确，可以有效处理各种文件创建场景

## 5. 测试计划

### 5.1 单元测试
   
1. **TaskExecutor 文件验证逻辑测试（test_file_validation.py）**:
   - 测试文件验证逻辑能否正确识别和报告缺失文件
   - 验证当文件未创建时，任务正确返回失败状态
   - 测试不同路径情况（相对路径、绝对路径）下的文件检查

2. **提示词生成测试（test_prompt_generation.py）**:
   - 测试改进后的 _prepare_context_aware_prompt 方法
   - 验证生成的提示词是否正确强调文件创建的重要性
   - 确认提示词中包含清晰的文件创建指导

3. **TaskPlanner 任务生成测试（test_task_normalization.py）**:
   - 测试规划者能否生成包含正确 output_files 结构的任务定义
   - 验证任务规范化过程中是否正确验证必要字段

### 5.2 集成测试

1. **文件依赖链测试（test_file_dependencies.py）**:
   - 测试任务链中的文件依赖关系
   - 验证当前置任务文件未创建时，系统是否正确处理错误

2. **错误处理和恢复测试**:
   - 验证系统在文件创建失败时能否提供明确错误信息
   - 测试规划者能否基于执行失败的信息调整后续计划

### 5.3 端到端测试

1. **针对已有样例测试**:
   - 测试现有任务示例 `/examples/demo_subtasks/sample_subtasks.json`
   - 验证系统能否正确处理多种类型文件（文本、图像等）

2. **系统鲁棒性测试**:
   - 测试极端情况下的系统表现（大文件、特殊文件名等）
   - 验证错误报告机制的有效性

## 6. 预期成果与实际效果

### 6.1 预期成果

1. **更可靠的任务执行机制**：
   - 执行者能够正确创建所有预期文件
   - 任务失败时提供明确错误信息，而非生成占位符掩盖问题

2. **更清晰的任务间依赖处理**：
   - 确保后续任务使用的是实际创建的文件，而非占位符
   - 文件依赖路径传递准确无误

3. **更高效的调试体验**：
   - 错误信息直接指出具体问题（哪些文件未创建）
   - 系统行为更加透明，问题更容易定位和解决

### 6.2 实际效果

基于已完成的修改和测试，我们实现了所有预期目标：

✅ **可靠性提高**：系统不再创建占位符文件，而是明确报告哪些文件未创建  
✅ **透明度提高**：任务失败原因更加明确，直接指出缺失的文件  
✅ **指令清晰度**：提示词中明确强调文件创建的重要性  
✅ **规范一致性**：确保所有任务都有正确定义的输出文件  
✅ **错误处理改进**：将错误信息保存到日志而非创建误导性的成功文件  

这次重构针对具体代码实现进行精确修改，保持系统原有架构不变，同时解决文件创建和验证的具体问题，使系统更加可靠和可预测。测试结果表明这些修改有效地解决了我们所面临的问题。

## 7. 后续步骤与建议

完成单元测试后，建议按以下步骤继续验证系统的稳定性和有效性：

### 7.1 计划功能测试

1. **验证计划生成功能**:
   ```bash
   # 使用测试模拟器运行计划功能测试
   python tests/run_plan_cli_test.py "分析一篇关于人工智能的论文" --output test_output/plan_test
   ```

   该测试程序可帮助验证：
   - 计划生成流程是否正确
   - 任务分解是否包含所需的output_files字段
   - 生成的任务依赖结构是否合理

2. **运行单元测试**:
   ```bash
   # 运行计划功能的单元测试
   python tests/test_plan_command.py
   ```

### 7.2 集成测试

1. **运行实际任务链测试**:
   ```bash
   python src/cli.py run-subtasks -f examples/demo_subtasks/sample_subtasks.json --logs-dir ./test_output
   ```

2. **故障注入测试**:
   已创建故障测试用例，可以使用以下命令运行：
   ```bash
   # 测试完全缺失文件情况
   python src/cli.py run-subtasks -f examples/failing_tasks/missing_files_test.json --logs-dir ./test_output/missing_files

   # 测试部分文件缺失情况
   python src/cli.py run-subtasks -f examples/failing_tasks/partial_files_test.json --logs-dir ./test_output/partial_files
   ```
   
   这些测试用例将验证：
   - 系统能否正确识别并报告缺失文件
   - 当前置任务未创建所需文件时的错误处理
   - 各种文件缺失场景下的系统行为

### 7.2 端到端验证

1. **执行完整任务流程**:
   - 使用真实的复杂任务测试完整工作流
   - 验证所有文件创建和依赖处理是否正确
   
2. **性能验证**:
   - 测试大型任务链的执行效率
   - 验证文件依赖关系的正确处理不会引入额外开销

### 7.3 持续集成与监控

1. **添加监控点**:
   - 为文件创建和验证逻辑添加关键日志点
   - 收集和分析文件处理相关的性能指标
   
2. **完善错误处理**:
   - 持续优化错误消息的可读性和信息量
   - 建立恢复机制，使系统能在特定错误情况下自动调整

实施这些后续测试和优化将确保重构的改进在各种实际使用场景中有效且稳定。