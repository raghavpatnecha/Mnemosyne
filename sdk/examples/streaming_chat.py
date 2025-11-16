"""
Streaming chat example with SSE (Server-Sent Events).

This example demonstrates:
- Real-time streaming chat responses
- Session management
- Chat history retrieval
- Source citation tracking
"""

from mnemosyne import Client
from uuid import UUID

# Initialize client
client = Client(api_key="your_api_key_here")

# Optional: Filter by collection
COLLECTION_ID = None  # Set to UUID("...") to filter by collection


def streaming_chat_basic():
    """Basic streaming chat example"""

    print("=" * 60)
    print("BASIC STREAMING CHAT")
    print("=" * 60)

    message = "What are the key components of a RAG system?"

    print(f"\nUser: {message}\n")
    print("Assistant: ", end="", flush=True)

    for chunk in client.chat.chat(
        message=message,
        stream=True,
    ):
        print(chunk, end="", flush=True)

    print("\n")


def multi_turn_conversation():
    """Multi-turn conversation with session management"""

    print("\n" + "=" * 60)
    print("MULTI-TURN CONVERSATION")
    print("=" * 60)

    # Create a conversation session
    session_id = None

    messages = [
        "What is retrieval-augmented generation?",
        "How does it improve over standard language models?",
        "What are the main challenges in implementing RAG?",
        "Can you give me an example use case?",
    ]

    for i, message in enumerate(messages, 1):
        print(f"\n[Turn {i}]")
        print(f"User: {message}\n")
        print("Assistant: ", end="", flush=True)

        current_session_id = session_id
        for chunk in client.chat.chat(
            message=message,
            session_id=current_session_id,
            top_k=5,
            stream=True,
        ):
            # First chunk contains session_id in metadata (in real implementation)
            # For now, we just stream the text
            print(chunk, end="", flush=True)

        print("\n")

    print("\n✓ Conversation complete!")


def chat_with_sources():
    """Chat with source tracking and collection filtering"""

    print("\n" + "=" * 60)
    print("CHAT WITH SOURCE CITATIONS")
    print("=" * 60)

    message = "What are the best practices for chunking documents in RAG?"

    print(f"\nUser: {message}\n")

    # Note: Source tracking requires non-streaming mode for structured response
    # In streaming mode, sources are sent separately
    print("Assistant (streaming):\n")
    for chunk in client.chat.chat(
        message=message,
        collection_id=COLLECTION_ID,
        top_k=5,
        stream=True,
    ):
        print(chunk, end="", flush=True)

    print("\n")


def view_chat_history():
    """Retrieve and display chat history"""

    print("\n" + "=" * 60)
    print("CHAT HISTORY")
    print("=" * 60)

    # List all sessions
    sessions = client.chat.list_sessions(limit=10)

    print(f"\nFound {len(sessions)} chat sessions:\n")

    for i, session in enumerate(sessions, 1):
        print(f"{i}. Session {session.id}")
        print(f"   Created: {session.created_at}")
        print(f"   Messages: {session.message_count}")
        print(f"   Last message: {session.last_message_at}")

        # Get messages for this session
        messages = client.chat.get_session_messages(session.id)

        print(f"\n   Conversation:")
        for msg in messages[:4]:  # Show first 4 messages
            role = msg.role.upper()
            content_preview = msg.content[:100] + ("..." if len(msg.content) > 100 else "")
            print(f"   {role}: {content_preview}")

        if len(messages) > 4:
            print(f"   ... ({len(messages) - 4} more messages)")

        print()


def interactive_chat():
    """Interactive chat loop"""

    print("\n" + "=" * 60)
    print("INTERACTIVE CHAT MODE")
    print("=" * 60)
    print("\nType 'quit' to exit, 'history' to view messages\n")

    session_id = None

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("\n👋 Goodbye!")
                break

            if user_input.lower() == "history":
                if session_id:
                    messages = client.chat.get_session_messages(session_id)
                    print(f"\n📜 Chat History ({len(messages)} messages):")
                    for msg in messages:
                        role = "You" if msg.role == "user" else "Assistant"
                        print(f"\n{role}: {msg.content}")
                    print()
                else:
                    print("\n📜 No chat history yet. Start a conversation!\n")
                continue

            # Stream response
            print("Assistant: ", end="", flush=True)
            for chunk in client.chat.chat(
                message=user_input,
                session_id=session_id,
                stream=True,
            ):
                print(chunk, end="", flush=True)

            print("\n")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def main():
    """Run chat examples"""

    print("\nMnemosyne Streaming Chat Examples\n")

    # Example 1: Basic streaming
    streaming_chat_basic()

    # Example 2: Multi-turn conversation
    multi_turn_conversation()

    # Example 3: Chat with sources
    chat_with_sources()

    # Example 4: View history
    view_chat_history()

    # Example 5: Interactive mode (commented out for automation)
    # print("\nStarting interactive mode...")
    # interactive_chat()

    print("\n" + "=" * 60)
    print("CHAT EXAMPLES COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    finally:
        client.close()
