"""
Unit tests for the GroupChat class.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from typing import Dict, Any, List

from chat_modes.group_chat import GroupChat, GroupChatFactory


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, name: str, responses: List[str] = None):
        self.name = name
        self.responses = responses or [f"Response from {name}"]
        self.response_index = 0
        self.generate_response = AsyncMock()
        
        # Configure the mock to return responses in sequence
        async def side_effect(*args, **kwargs):
            response = self.responses[self.response_index % len(self.responses)]
            self.response_index += 1
            return response
            
        self.generate_response.side_effect = side_effect


@pytest.fixture
def agents():
    """Fixture providing mock agents for testing."""
    return {
        "expert1": MockAgent("Expert 1", ["Expert 1's first response", "Expert 1's second response"]),
        "expert2": MockAgent("Expert 2", ["Expert 2's first response", "Expert 2's second response"]),
        "expert3": MockAgent("Expert 3", ["Expert 3's first response", "Expert 3's second response"]),
    }


@pytest.fixture
def facilitator():
    """Fixture providing a mock facilitator agent."""
    return MockAgent("Facilitator", [
        "As facilitator, I'll guide this discussion.",
        "Let me summarize the first round and guide the next steps."
    ])


@pytest.mark.asyncio
async def test_group_chat_init(agents):
    """Test GroupChat initialization."""
    # Basic initialization
    chat = GroupChat(agents, "Discuss the topic")
    
    assert chat.agents == agents
    assert chat.initial_prompt == "Discuss the topic"
    assert chat.max_rounds == 10  # Default value
    assert chat.speaking_order == "round_robin"  # Default value
    assert not chat.active
    assert chat.current_round == 0
    
    # Custom configuration
    config = {
        "max_rounds": 5,
        "speaking_order": "dynamic",
    }
    chat = GroupChat(agents, "Custom topic", config)
    
    assert chat.max_rounds == 5
    assert chat.speaking_order == "dynamic"


@pytest.mark.asyncio
async def test_initiate_chat(agents):
    """Test initiating a group chat."""
    chat = GroupChat(agents, "Discuss AI ethics")
    
    # Initiate chat
    response = await chat.initiate_chat("Let's discuss AI ethics")
    
    # Verify the chat was properly initiated
    assert chat.active
    assert chat.current_round == 1
    assert len(chat.history) == 2  # Initial message + first agent's response
    assert chat.history[0]["sender"] == "user"
    assert chat.history[0]["message"] == "Let's discuss AI ethics"
    assert chat.history[0]["round"] == 0
    
    # Verify first agent was called correctly
    first_agent_name = list(agents.keys())[0]
    agents[first_agent_name].generate_response.assert_called_once()
    

@pytest.mark.asyncio
async def test_continue_chat(agents):
    """Test continuing a group chat conversation."""
    chat = GroupChat(agents, "Discuss AI ethics")
    
    # Initiate chat first
    await chat.initiate_chat("Let's discuss AI ethics")
    
    # Continue chat to get next response
    response = await chat.continue_chat()
    
    # Verify the chat continued properly
    assert chat.active
    assert len(chat.history) == 3  # Initial + first agent + second agent
    
    # The second agent should have been called
    second_agent_name = list(agents.keys())[1]
    agents[second_agent_name].generate_response.assert_called_once()
    
    # Continue again for the third agent
    response = await chat.continue_chat()
    
    # Verify the third agent was called
    assert len(chat.history) == 4  # Initial + three agents
    third_agent_name = list(agents.keys())[2]
    agents[third_agent_name].generate_response.assert_called_once()


@pytest.mark.asyncio
async def test_facilitator_role(agents, facilitator):
    """Test group chat with a facilitator."""
    # Add facilitator to agents
    agents_with_facilitator = agents.copy()
    agents_with_facilitator["facilitator"] = facilitator
    
    # Create chat with facilitator configuration
    config = {
        "facilitator": "facilitator"
    }
    chat = GroupChat(agents_with_facilitator, "Discuss climate change", config)
    
    # Initiate chat
    response = await chat.initiate_chat("Let's discuss climate change solutions")
    
    # Verify facilitator was the first to respond
    assert chat.active
    assert len(chat.history) == 2
    assert chat.history[1]["sender"] == "facilitator"
    
    # Continue chat for the next speaker (which should not be facilitator again)
    response = await chat.continue_chat()
    
    # Verify a non-facilitator agent responded
    assert len(chat.history) == 3
    assert chat.history[2]["sender"] != "facilitator"


@pytest.mark.asyncio
async def test_round_completion(agents):
    """Test completion of a discussion round."""
    chat = GroupChat(agents, "Discuss AI ethics")
    
    # Initiate chat
    await chat.initiate_chat("Let's discuss AI ethics")
    
    # Complete the first round (3 agents = 3 turns)
    await chat.continue_chat()  # Second agent
    await chat.continue_chat()  # Third agent
    
    # Verify that the round was completed
    assert chat.current_round == 1
    assert len(chat.spoken_in_round) == 3  # All agents have spoken
    
    # Start next round
    response = await chat.continue_chat()
    
    # Verify new round started and first agent speaks again
    assert chat.current_round == 2
    first_agent_name = list(agents.keys())[0]
    assert chat.history[-1]["sender"] == first_agent_name


@pytest.mark.asyncio
async def test_custom_speaking_order(agents):
    """Test group chat with custom speaking order function."""
    # Define a custom speaking order function
    def custom_order(agents, history, spoken):
        """Always pick expert2 if available, otherwise pick the first available."""
        if "expert2" not in spoken:
            return "expert2"
        for agent in agents:
            if agent not in spoken:
                return agent
        return list(agents.keys())[0]  # Default to first agent
    
    # Create chat with custom speaking order
    config = {
        "speaking_order": custom_order
    }
    chat = GroupChat(agents, "Discuss AI ethics", config)
    
    # Initiate chat
    await chat.initiate_chat("Let's discuss AI ethics")
    
    # Verify that expert2 speaks first (due to our custom order function)
    assert chat.history[1]["sender"] == "expert2"


@pytest.mark.asyncio
async def test_external_message(agents):
    """Test adding an external message during the chat."""
    chat = GroupChat(agents, "Discuss AI ethics")
    
    # Initiate chat
    await chat.initiate_chat("Let's discuss AI ethics")
    
    # Add an external message and continue
    response = await chat.continue_chat("Here's some additional info", "external_user")
    
    # Verify the external message was added
    assert len(chat.history) == 4  # Initial + first agent + external + second agent
    assert chat.history[1]["sender"] == list(agents.keys())[0]
    assert chat.history[2]["sender"] == "external_user"
    assert chat.history[2]["message"] == "Here's some additional info"
    assert chat.history[3]["sender"] == list(agents.keys())[1]  # Second agent responds after external message


@pytest.mark.asyncio
async def test_end_chat(agents):
    """Test ending the group chat."""
    chat = GroupChat(agents, "Discuss AI ethics")
    
    # Initiate and run a bit
    await chat.initiate_chat("Let's discuss AI ethics")
    await chat.continue_chat()
    
    # End the chat
    results = chat.end_chat()
    
    # Verify the chat was properly ended
    assert not chat.active
    assert "history" in results
    assert "context" in results
    assert "rounds" in results
    assert results["rounds"] == chat.current_round


@pytest.mark.asyncio
async def test_max_rounds(agents):
    """Test that chat stops after max_rounds."""
    # Create chat with only 1 max round
    config = {
        "max_rounds": 1
    }
    chat = GroupChat(agents, "Discuss AI ethics", config)
    
    # Initiate and complete one round
    await chat.initiate_chat("Let's discuss AI ethics")
    await chat.continue_chat()  # Second agent
    await chat.continue_chat()  # Third agent
    
    # Try to continue to the next round
    response = await chat.continue_chat()
    
    # Verify that the chat terminated due to max rounds
    assert not chat.active
    assert "maximum number of rounds" in response


@pytest.mark.asyncio
async def test_factory_create(agents):
    """Test the GroupChatFactory create method."""
    chat = GroupChatFactory.create(
        agents, 
        "Discuss AI ethics",
        config={"max_rounds": 3}
    )
    
    assert isinstance(chat, GroupChat)
    assert chat.agents == agents
    assert chat.initial_prompt == "Discuss AI ethics"
    assert chat.max_rounds == 3


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])