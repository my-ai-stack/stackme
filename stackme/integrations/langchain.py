"""
Stackme LangChain Integration

This module provides LangChain memory components that integrate stackme's
Context with LangChain's memory system.

Usage:
    from stackme import Context
    from stackme.integrations.langchain import StackmeMemory

    # Create stackme context
    ctx = Context(user_id="user123")

    # Create LangChain memory wrapper
    memory = StackmeMemory(context=ctx)

    # Use with LangChain chains
    from langchain_openai import ChatOpenAI
    from langchain.chains import ConversationChain

    llm = ChatOpenAI(model="gpt-4")
    chain = ConversationChain(llm=llm, memory=memory)

    # The chain will now use stackme for memory
    response = chain.predict(input="My name is John and I work at Acme Corp")
    # stackme automatically stores the conversation and extracts facts

    response = chain.predict(input="What's my name?")
    # Should remember "John" from context
"""

from typing import Any, Dict, List, Optional, Union

from langchain_core.memory import BaseMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.outputs import ChatGenerationChunk, GenerationChunk
from langchain_core.runnables import Runnable, RunnableMap, chain
from langchain_core.runnables.config import RunnableConfig

from stackme import Context


class StackmeMemory(BaseMemory):
    """
    LangChain memory component that wraps stackme's Context.

    This memory implementation stores conversations in stackme's three-tier
    memory system (Session, ShortTerm, LongTerm) and provides semantic
    retrieval for context-aware responses.

    Args:
        context: A stackme Context instance. If not provided, a new one will be created.
        session_id: Session identifier for isolating conversations.
        memory_key: The key to use for memory variables in the prompt. Default: "history".
        input_key: The key for user input in the input dict. Default: "input".
        output_key: The key for AI output in the output dict. Default: "output".
        return_messages: Whether to return messages in load_memory_variables. Default: True.
        k: Number of recent messages to return. Default: 5.
        persist_facts: Whether to persist facts to long-term memory. Default: True.

    Example:
        from stackme import Context
        from stackme.integrations.langchain import StackmeMemory

        ctx = Context(user_id="my-user")
        memory = StackmeMemory(context=ctx)

        # Use in a ConversationChain
        from langchain.chains import ConversationChain
        chain = ConversationChain(llm=ChatOpenAI(), memory=memory)

        chain.predict(input="I'm building a fintech startup")
    """

    def __init__(
        self,
        context: Optional[Context] = None,
        session_id: str = "default",
        memory_key: str = "history",
        input_key: str = "input",
        output_key: str = "output",
        return_messages: bool = True,
        k: int = 5,
        persist_facts: bool = True,
    ):
        super().__init__()
        self.context = context or Context(user_id=session_id)
        self.session_id = session_id
        self.memory_key = memory_key
        self.input_key = input_key
        self.output_key = output_key
        self.return_messages = return_messages
        self.k = k
        self.persist_facts = persist_facts

    @property
    def memory_variables(self) -> List[str]:
        """Return memory variables that this memory class supports."""
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load memory variables for context.

        This method retrieves relevant context from stackme based on the input
        and returns it in a format suitable for the prompt template.

        Args:
            inputs: Input dictionary, should contain the input_key value.

        Returns:
            Dictionary with memory_key containing the context string or messages.
        """
        # Get the input query to search for relevant context
        input_text = inputs.get(self.input_key, "")

        if input_text:
            # Search for relevant context semantically
            relevant_context = self.context.get_relevant(input_text, top_k=self.k)
        else:
            # No input, get recent session history
            history = self.context.get_session_history(last_n=self.k)
            relevant_context = self._format_history(history)

        if self.return_messages:
            # Return as messages for chat models
            messages = self._get_chat_messages(inputs.get(self.input_key, ""))
            return {self.memory_key: messages}
        else:
            # Return as string for non-chat models
            return {self.memory_key: relevant_context}

    def _get_chat_messages(self, query: str = "") -> List[BaseMessage]:
        """Get messages formatted for chat models."""
        messages = []

        # Get session history
        history = self.context.get_session_history(last_n=self.k)

        for turn in history:
            role = turn.get("role", "")
            content = turn.get("content", "")

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        # Add relevant context if there's a query
        if query:
            relevant = self.context.get_relevant(query, top_k=3)
            if relevant:
                # Add system context as a system message
                messages.insert(0, HumanMessage(content=f"Relevant context: {relevant}"))

        return messages

    def _format_history(self, history: List[Dict]) -> str:
        """Format history as a string for non-chat models."""
        if not history:
            return ""

        lines = []
        for turn in history:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """
        Save context from the current interaction.

        This method is called after an LLM response and stores both the
        user input and AI output to stackme's memory system.

        Args:
            inputs: Input dictionary containing the user input.
            outputs: Output dictionary containing the AI response.
        """
        # Extract input and output
        input_text = inputs.get(self.input_key, "")
        output_text = outputs.get(self.output_key, "")

        # Save user message
        if input_text:
            self.context.add_user_message(input_text)

        # Save AI response
        if output_text:
            self.context.add_ai_message(output_text)

    def clear(self) -> None:
        """Clear session memory (preserves long-term memory)."""
        self.context.clear_session()


class StackmeMessageHistory:
    """
    ChatMessageHistory-compatible class for use with RunnableWithMessageHistory.

    This class provides a ChatMessageHistory interface that can be used with
    LangChain's RunnableWithMessageHistory for LCEL-based applications.

    Args:
        context: A stackme Context instance.
        session_id: Session identifier (defaults to "default").

    Example:
        from stackme import Context
        from stackme.integrations.langchain import StackmeMessageHistory

        ctx = Context(user_id="user123")
        memory = StackmeMessageHistory(context=ctx)

        # Use with RunnableWithMessageHistory
        from langchain_core.runnables import RunnableWithMessageHistory

        chain = prompt | llm
        chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: memory,
            input_messages_key="question",
            history_messages_key="history"
        )

        response = chain_with_history.invoke(
            {"question": "What did I ask before?"},
            config={"configurable": {"session_id": "user123"}}
        )
    """

    def __init__(
        self,
        context: Optional[Context] = None,
        session_id: str = "default",
    ):
        self.context = context or Context(user_id=session_id)
        self.session_id = session_id

    def add_user_message(self, message: str) -> None:
        """Add a user message to the history."""
        self.context.add_user_message(message)

    def add_ai_message(self, message: str) -> None:
        """Add an AI message to the history."""
        self.context.add_ai_message(message)

    def add_message(self, message: BaseMessage) -> None:
        """Add a BaseMessage to the history."""
        if isinstance(message, HumanMessage):
            self.context.add_user_message(message.content)
        elif isinstance(message, AIMessage):
            self.context.add_ai_message(message.content)
        else:
            # Generic message - treat as user message
            self.context.add_user_message(message.content)

    def get_messages(self) -> List[BaseMessage]:
        """Get all messages as BaseMessage objects."""
        history = self.context.get_session_history()
        messages = []

        for turn in history:
            role = turn.get("role", "")
            content = turn.get("content", "")

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        return messages

    def clear(self) -> None:
        """Clear the message history."""
        self.context.clear_session()


def get_session_history(
    context: Optional[Context] = None,
    session_id: str = "default",
) -> StackmeMessageHistory:
    """
    Factory function for getting a session history instance.

    This function is designed to be used with RunnableWithMessageHistory's
    get_session_history parameter.

    Args:
        context: A stackme Context instance.
        session_id: Session identifier for the history.

    Returns:
        A StackmeMessageHistory instance.

    Example:
        from langchain_core.runnables import RunnableWithMessageHistory

        chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: get_session_history(session_id=session_id),
            input_messages_key="question",
            history_messages_key="history"
        )
    """
    # Create context with session_id as user_id if not provided
    if context is None:
        context = Context(user_id=session_id)

    return StackmeMessageHistory(context=context, session_id=session_id)


class StackmeRetrieverMemory(BaseMemory):
    """
    A LangChain memory that uses stackme as a retriever for context.

    This memory implementation focuses on semantic retrieval from stackme's
    long-term memory, making it ideal for applications where relevant context
    needs to be fetched based on the current query.

    Args:
        context: A stackme Context instance.
        memory_key: The key for memory variables. Default: "context".
        input_key: The key for user input. Default: "input".
        k: Number of relevant memories to retrieve. Default: 5.
        include_session_history: Whether to include session history. Default: True.

    Example:
        from stackme import Context
        from stackme.integrations.langchain import StackmeRetrieverMemory

        ctx = Context(user_id="my-user")
        memory = StackmeRetrieverMemory(context=ctx)

        # Add some facts
        ctx.add_fact("User prefers dark mode")
        ctx.add_fact("User works in fintech")

        # Use in a chain - will retrieve relevant context automatically
        from langchain.chains import LLMChain
        chain = LLMChain(prompt=prompt, llm=llm, memory=memory)
    """

    def __init__(
        self,
        context: Optional[Context] = None,
        memory_key: str = "context",
        input_key: str = "input",
        k: int = 5,
        include_session_history: bool = True,
    ):
        super().__init__()
        self.context = context or Context()
        self.memory_key = memory_key
        self.input_key = input_key
        self.k = k
        self.include_session_history = include_session_history

    @property
    def memory_variables(self) -> List[str]:
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load relevant context from stackme based on the input query."""
        input_text = inputs.get(self.input_key, "")

        # Get relevant context from long-term memory
        context = self.context.get_relevant(input_text, top_k=self.k)

        # Optionally include session history
        if self.include_session_history:
            session_history = self.context.get_session_history(last_n=self.k * 2)
            if session_history:
                history_str = self._format_history(session_history)
                if context:
                    context = f"{context}\n\n## Recent Conversation\n{history_str}"
                else:
                    context = f"## Recent Conversation\n{history_str}"

        return {self.memory_key: context}

    def _format_history(self, history: List[Dict]) -> str:
        """Format session history as string."""
        if not history:
            return ""

        lines = []
        for turn in history:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Save the conversation to stackme."""
        input_text = inputs.get(self.input_key, "")
        output_text = outputs.get(self.output_key, "")

        if input_text:
            self.context.add_user_message(input_text)

        if output_text:
            self.context.add_ai_message(output_text)

    def clear(self) -> None:
        """Clear session memory."""
        self.context.clear_session()


# Convenience function for creating memory with defaults
def create_stackme_memory(
    user_id: str = "default",
    embedding: str = "sentence-transformers",
    api_key: Optional[str] = None,
    **kwargs,
) -> StackmeMemory:
    """
    Create a StackmeMemory instance with default settings.

    Args:
        user_id: User identifier for the context.
        embedding: Embedding provider to use.
        api_key: API key for embeddings (if needed).
        **kwargs: Additional arguments for StackmeMemory.

    Returns:
        A StackmeMemory instance.

    Example:
        memory = create_stackme_memory(user_id="user123")
    """
    context = Context(user_id=user_id, embedding=embedding, api_key=api_key)
    return StackmeMemory(context=context, **kwargs)


__all__ = [
    "StackmeMemory",
    "StackmeMessageHistory",
    "StackmeRetrieverMemory",
    "get_session_history",
    "create_stackme_memory",
]