# AG2-Wrapper

AG2-Wrapper/ *����AG2AutoGen	F����w�(�Agent���߄(Л� ���e������!

## y��

AG2-Wrapper�Ř�AutoGenF�Л���

- ��API(�������!
- �w�:6/茌(�w�p
- Mn��LLM�AgentMn
- �	�w�߄��

## ���B

- Python 3.8+
- AutoGen 0.7.5��(conda��'ag2'-	

## ��

1. �;AG2��:

```bash
conda activate ag2
```

2. ��AG2-Wrapper:

```bash
cd /path/to/ag2-wrapper
pip install -e .
```

## (:�

### �,$Agent��

```python
from ag2_wrapper.core.wrapper import AG2Wrapper
from ag2_wrapper.core.config import create_openai_config

# �LLMMn
llm_config = create_openai_config(
    model="gpt-3.5-turbo",
    temperature=0.7
)

# �AG2Wrapper��
wrapper = AG2Wrapper()

# �$Agent��
chat = wrapper.create_two_agent_chat(
    assistant_config={
        "name": "�K",
        "system_message": "`/ *	.��AI�K�(-��T",
        "llm_config": llm_config
    },
    human_config={
        "name": "(7",
        "code_execution": True  # A��gL
    }
)

# /���
response = await chat.start("�� *����Qp�Python�p")
print(f"�K: {response}")

# ����
response = await chat.continue_chat("�(.�*�p")
print(f"�K: {response}")
```

### �w�:�

```python
from ag2_wrapper.core.wrapper import AG2Wrapper
from ag2_wrapper.integrations.tool_manager import AG2ToolManagerAdapter
from agent_tools.tool_manager import ToolManager

# ���w�h
external_tool_manager = ToolManager()
external_tool_manager.register_tool("weather", WeatherTool())

# ��wMh
tool_adapter = AG2ToolManagerAdapter(external_tool_manager)

# �AG2Wrapperv��w
wrapper = AG2Wrapper()
wrapper.integrate_tool_manager(tool_adapter)

# �$Agent��
chat = wrapper.create_two_agent_chat(
    assistant_config={"llm_config": llm_config},
    human_config={}
)

# /����K��(���w
response = await chat.start("�J���)")
```

## /���!

AG2-Wrapper�/���!

1. **TwoAgentChat**: $*AgentK����	
2. **SequentialChat**: Agent	z���
3. **GroupChat**: AgentvL��
4. **NestedChat**: /��LW
5. **Swarm**: �����O\

## y�ӄ

```
ag2_wrapper/
   core/               # 8���
      wrapper.py      # AG2Wrapper;{
      config.py       # Mn�
      tools.py        # �w�
   chat_modes/         # ��!��
      two_agent.py    # $Agent��
      sequential.py   # z���
      group_chat.py   # �J��
      nested.py       # LW��
      swarm.py        # SwarmO\!
   utils/              # �w�p
   integrations/       # ��
       tool_manager.py # �w�h�
```

## � ѡ

- ��iY��!SequentialChat, GroupChat, NestedChat, Swarm	
- �:�w���
- ����wMh
- ��Task Planner��
- Л�:��Y

## ���

[MIT License](LICENSE)