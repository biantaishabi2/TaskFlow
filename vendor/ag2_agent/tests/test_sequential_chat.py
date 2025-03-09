import pytest
from ag2_agent import create_orchestration_manager
from utils import MockAgent, SimpleHumanAgent, SimpleAssistantAgent
from chat_modes import SequentialChat
from typing import Dict, Any


def test_create_sequential_chat():
    """Test creating a sequential chat"""
    manager = create_orchestration_manager()
    
    # Register agents
    manager.register_agent("user", SimpleHumanAgent(name="User"))
    manager.register_agent("assistant", SimpleAssistantAgent(name="Assistant"))
    manager.register_agent("reviewer", SimpleAssistantAgent(name="Reviewer"))
    
    # Create chat with three agents
    chat = manager.create_chat(
        mode="sequential",
        agents={"user": "user", "assistant": "assistant", "reviewer": "reviewer"},
        initial_prompt="Let's solve a problem in sequence",
        config={"max_turns": 5}
    )
    
    assert chat is not None
    assert isinstance(chat, SequentialChat)
    assert len(chat.agents) == 3
    assert chat.max_turns == 5
    assert chat.agent_order == ["user", "assistant", "reviewer"]


def test_sequential_chat_basic_flow():
    """Test the basic flow of a sequential chat with multiple agents"""
    # Create agents with predetermined responses
    assistant = MockAgent(name="Assistant", responses=["Here's a solution to your Python problem"])
    reviewer = MockAgent(name="Reviewer", responses=["The solution looks good but could be optimized"])
    
    # Create the chat directly - starting with assistant since we want to skip user
    chat = SequentialChat(
        agents={"assistant": assistant, "reviewer": reviewer},
        initial_prompt="Let's solve a problem in sequence",
        config={"max_turns": 5}
    )
    
    # Start chat with a problem statement
    response = chat.initiate_chat("I need help with a Python problem", sender="user")
    assert response == "Here's a solution to your Python problem"
    assert chat.current_step == 1  # Should be at reviewer now
    
    # Continue to reviewer
    response = chat.continue_chat()
    assert response == "The solution looks good but could be optimized"
    assert chat.current_step == 2  # Should be after reviewer
    assert chat.is_complete() == True  # All agents have responded
    
    # Get history
    history = chat.get_chat_history()
    assert len(history) == 3  # Initial + 2 responses
    assert history[0]["sender"] == "user"
    assert history[1]["sender"] == "assistant"
    assert history[2]["sender"] == "reviewer"


def test_sequential_chat_with_context():
    """Test sequential chat with context passing between agents"""
    # Create agents
    translator1 = MockAgent(name="FrenchTranslator", responses=["'hello' in French is 'bonjour'"])
    translator2 = MockAgent(name="SpanishTranslator", responses=["'hello' in Spanish is 'hola'"])
    
    # For debugging
    debug_info = []
    
    # Custom context handler that extracts translations
    def extract_translations(previous_context: Dict[str, Any], current_info: Dict[str, Any]) -> Dict[str, Any]:
        updated_context = previous_context.copy()
        
        # Debug info
        debug_info.append(f"Processing context update: {current_info}")
        
        # Extract translations from responses
        if 'agent' in current_info and 'response' in current_info:
            response = current_info['response']
            agent = current_info['agent']
            
            debug_info.append(f"Agent: {agent}, Response: {response}")
            
            # Use direct comparison for this test instead of complex parsing
            if agent == 'french' and response == "'hello' in French is 'bonjour'":
                updated_context['french_translation'] = 'bonjour'
                debug_info.append(f"Added french_translation: bonjour")
            elif agent == 'spanish' and response == "'hello' in Spanish is 'hola'":
                updated_context['spanish_translation'] = 'hola'
                debug_info.append(f"Added spanish_translation: hola")
        
        # Add all other info
        for key, value in current_info.items():
            if key not in ['agent']:
                updated_context[key] = value
        
        debug_info.append(f"Updated context: {updated_context}")
        return updated_context
    
    # Create chat with context handler
    chat = SequentialChat(
        agents={"french": translator1, "spanish": translator2},
        initial_prompt="Translate in sequence",
        context_handler=extract_translations,
        config={"max_turns": 5}
    )
    
    # Start chat
    response = chat.initiate_chat("I need to translate 'hello' to French and then Spanish", sender="user")
    assert response == "'hello' in French is 'bonjour'"
    assert 'french_translation' in chat.context, f"french_translation not in context. Debug: {debug_info}"
    assert chat.context['french_translation'] == 'bonjour'
    
    # Continue to Spanish translator
    response = chat.continue_chat()
    assert response == "'hello' in Spanish is 'hola'"
    
    # Print debug information for diagnosing the issue
    print("\nDebug Info:")
    for line in debug_info:
        print(f"  {line}")
    print(f"\nFinal context: {chat.context}")
    print(f"Response from Spanish translator: {response}")
    
    # Modified assertion to better understand the issue
    if 'spanish_translation' in chat.context:
        spanish_value = chat.context['spanish_translation']
        assert spanish_value == 'hola', f"spanish_translation = '{spanish_value}', expected 'hola'"
    else:
        assert 'spanish_translation' in chat.context, f"spanish_translation not in context {chat.context}"
    
    # End chat and check final context
    result = chat.end_chat()
    assert 'french_translation' in result['context']
    assert 'spanish_translation' in result['context']
    assert result['context']['french_translation'] == 'bonjour'
    assert result['context']['spanish_translation'] == 'hola'


def test_sequential_chat_callbacks():
    """Test registering and triggering callbacks in sequential chat"""
    # Create agents
    agent1 = MockAgent(name="Agent1", responses=["Response from Agent1"])
    agent2 = MockAgent(name="Agent2", responses=["Response from Agent2"])
    
    # Create chat
    chat = SequentialChat(
        agents={"agent1": agent1, "agent2": agent2},
        initial_prompt="Test callbacks",
        config={}
    )
    
    # Track callback calls
    callback_data = {
        "message_sent": 0,
        "response_received": 0,
        "chat_ended": 0,
        "last_context": None
    }
    
    # Set up callbacks
    def on_message_sent(data):
        callback_data["message_sent"] += 1
    
    def on_response_received(data):
        callback_data["response_received"] += 1
        if "context" in data:
            callback_data["last_context"] = data["context"]
    
    def on_chat_ended(data):
        callback_data["chat_ended"] += 1
        if "context" in data:
            callback_data["last_context"] = data["context"]
    
    # Register callbacks
    chat.register_callback("message_sent", on_message_sent)
    chat.register_callback("response_received", on_response_received)
    chat.register_callback("chat_ended", on_chat_ended)
    
    # Test triggering callbacks
    chat.initiate_chat("Initial message")
    assert callback_data["message_sent"] == 1
    assert callback_data["response_received"] == 1
    
    chat.continue_chat()
    assert callback_data["message_sent"] == 1  # No new message sent
    assert callback_data["response_received"] == 2  # Second agent response
    
    chat.end_chat()
    assert callback_data["chat_ended"] == 1
    assert callback_data["last_context"] is not None


def test_sequential_chat_with_additional_input():
    """Test sequential chat with additional input between steps"""
    # Create agents
    agent1 = MockAgent(name="Agent1", responses=["First step completed"])
    agent2 = MockAgent(name="Agent2", responses=["Processed additional input and completed second step"])
    
    # Create chat
    chat = SequentialChat(
        agents={"agent1": agent1, "agent2": agent2},
        initial_prompt="Start sequential process",
        config={}
    )
    
    # Start chat
    response = chat.initiate_chat("Start the process")
    assert response == "First step completed"
    
    # Continue with additional input
    response = chat.continue_chat("Here's additional information for step 2", sender="user")
    assert response == "Processed additional input and completed second step"
    
    # Check history contains the additional input
    history = chat.get_chat_history()
    assert len(history) == 4  # Initial + agent1 response + additional input + agent2 response
    assert history[2]["sender"] == "user"
    assert "additional information" in history[2]["message"]