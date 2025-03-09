import pytest
from ag2_agent import create_orchestration_manager
from utils import MockAgent, SimpleHumanAgent, SimpleAssistantAgent
from chat_modes import TwoAgentChat


def test_create_orchestration_manager():
    """Test creating an orchestration manager"""
    manager = create_orchestration_manager()
    assert manager is not None
    assert hasattr(manager, "register_agent")
    assert hasattr(manager, "create_chat")
    assert "two_agent" in manager.chat_factories


def test_register_agents():
    """Test registering agents"""
    manager = create_orchestration_manager()
    
    # Register a human agent
    manager.register_agent("human", SimpleHumanAgent(name="Human"))
    assert "human" in manager.agent_registry
    
    # Register an assistant agent
    manager.register_agent("assistant", SimpleAssistantAgent(name="Assistant"))
    assert "assistant" in manager.agent_registry
    
    # Test registering with same name (should fail)
    with pytest.raises(ValueError):
        manager.register_agent("human", SimpleHumanAgent(name="Human2"))
    
    # Test overwrite flag
    manager.register_agent("human", SimpleHumanAgent(name="Human2"), overwrite=True)
    assert manager.agent_registry["human"].name == "Human2"


def test_create_two_agent_chat():
    """Test creating a two-agent chat"""
    manager = create_orchestration_manager()
    
    # Register agents
    manager.register_agent("human", SimpleHumanAgent(name="Human"))
    manager.register_agent("assistant", SimpleAssistantAgent(name="Assistant"))
    
    # Create chat
    chat = manager.create_chat(
        mode="two_agent",
        agents={"user": "human", "assistant": "assistant"},
        initial_prompt="Hello!",
        config={"max_turns": 5}
    )
    
    assert chat is not None
    assert isinstance(chat, TwoAgentChat)
    assert len(chat.agents) == 2
    assert chat.max_turns == 5


def test_two_agent_chat_conversation():
    """Test a basic conversation between two agents"""
    # Create agents directly
    human = MockAgent(name="Human", responses=["Hello!", "How are you?", "Goodbye!"])
    assistant = MockAgent(name="Assistant", responses=["Hi there!", "I'm doing well, thank you!", "Bye!"])
    
    # Create the chat directly (without manager)
    chat = TwoAgentChat(
        agents={"user": human, "assistant": assistant},
        initial_prompt="Let's start a conversation",
        config={"max_turns": 5}
    )
    
    # Start chat - User sends "Hello!", Assistant responds "Hi there!"
    response = chat.initiate_chat("Hello!", sender="user")
    assert response == "Hi there!"
    assert len(chat.chat_history) == 2
    
    # Continue chat - After initiate_chat, the next speaker should be the user again
    # So when continuing, the assistant should respond to the user's next message
    # In our implementation, when continue_chat is called without a message,
    # it uses the last message in history and gets a response from the listener 
    # After swapping roles, the assistant is now the listener
    response = chat.continue_chat("How are you?", sender="user")
    assert response == "I'm doing well, thank you!"
    assert len(chat.chat_history) == 4  # User message + Assistant response = 2 more messages
    
    # End chat
    result = chat.end_chat()
    assert result["turn_count"] == 2


def test_callbacks():
    """Test registering and triggering callbacks"""
    # Create agents
    human = MockAgent(name="Human", responses=["Hello!"])
    assistant = MockAgent(name="Assistant", responses=["Hi there!"])
    
    # Create chat
    chat = TwoAgentChat(
        agents={"user": human, "assistant": assistant},
        initial_prompt="Test",
        config={}
    )
    
    # Set up test callback
    callback_data = {"called": False, "data": None}
    
    def test_callback(data):
        callback_data["called"] = True
        callback_data["data"] = data
    
    # Register callback
    chat.register_callback("message_sent", test_callback)
    
    # Trigger callback by initiating chat
    chat.initiate_chat("Hello!", sender="user")
    
    # Check callback was called
    assert callback_data["called"]
    assert callback_data["data"]["sender"] == "user"
    assert callback_data["data"]["message"] == "Hello!"