# from dotenv import load_dotenv
# from langchain import hub
# from langchain.agents import AgentExecutor, create_structured_chat_agent
# from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
# from langchain_core.tools import Tool
# from langchain_openai import ChatOpenAI
# from langchain.memory import ConversationBufferWindowMemory


# import os
# # Load environment variables from .env file
# load_dotenv()


# # Define Tools
# def get_current_time(*args, **kwargs):
#     """Returns the current time in H:MM AM/PM format."""
#     import datetime

#     now = datetime.datetime.now()
#     return now.strftime("%I:%M %p")


# def search_wikipedia(query):
#     """Searches Wikipedia and returns the summary of the first result."""
#     from wikipedia import summary

#     try:
#         # Limit to two sentences for brevity
#         return summary(query, sentences=2)
#     except:
#         return "I couldn't find any information on that."


# # Define the tools that the agent can use
# tools = [
#     Tool(
#         name="Time",
#         func=get_current_time,
#         description="Useful for when you need to know the current time.",
#     ),
#     Tool(
#         name="Wikipedia",
#         func=search_wikipedia,
#         description="Useful for when you need to know information about a topic.",
#     ),
# ]

# # Load the correct JSON Chat Prompt from the hub
# prompt = hub.pull("hwchase17/structured-chat-agent")
# # Load environment variables from .env file
# load_dotenv()



# # Initialize a ChatOpenAI model
# llm = ChatOpenAI(model="gpt-4")

# # Create a structured Chat Agent with Conversation Buffer Memory
# # ConversationBufferMemory stores the conversation history, allowing the agent to maintain context across interactions
# # memory = ConversationBufferMemory(
# #     memory_key="chat_history", return_messages=True)


# # # Use it in memory
# # memory = ConversationBufferMemory(
# #     memory_key="chat_history",
# #     return_messages=True
# # )


# memory = ConversationBufferWindowMemory(
#     memory_key="chat_history",
#     return_messages=True,
#     k=5  # Specify how many past interactions to keep in memory
# )

# # create_structured_chat_agent initializes a chat agent designed to interact using a structured prompt and tools
# # It combines the language model (llm), tools, and prompt to create an interactive agent
# agent = create_structured_chat_agent(llm=llm, tools=tools, prompt=prompt)

# # AgentExecutor is responsible for managing the interaction between the user input, the agent, and the tools
# # It also handles memory to ensure context is maintained throughout the conversation
# agent_executor = AgentExecutor.from_agent_and_tools(
#     agent=agent,
#     tools=tools,
#     verbose=True,
#     memory=memory,  # Use the conversation memory to maintain context
#     handle_parsing_errors=True,  # Handle any parsing errors gracefully
# )

# # Initial system message to set the context for the chat
# # SystemMessage is used to define a message from the system to the agent, setting initial instructions or context
# initial_message = "You are an AI assistant that can provide helpful answers using available tools.\nIf you are unable to answer, you can use the following tools: Time and Wikipedia."
# memory.chat_memory.add_message(SystemMessage(content=initial_message))

# # Chat Loop to interact with the user
# while True:
#     user_input = input("User: ")
#     if user_input.lower() == "exit":
#         break

#     # Add the user's message to the conversation memory
#     memory.chat_memory.add_message(HumanMessage(content=user_input))

#     # Invoke the agent with the user input and the current chat history
#     response = agent_executor.invoke({"input": user_input})
#     print("Bot:", response["output"])

#     # Add the agent's response to the conversation memory
#     memory.chat_memory.add_message(AIMessage(content=response["output"]))
    
from dotenv import load_dotenv
from langchain import hub
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from flask_cors import CORS
import os
from flask import Flask, request, jsonify, render_template # Import Flask for the web server
# Load environment variables from .env file (ensure .env file exists in your project)
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

CORS(app)

# Define Tools
def get_current_time(*args, **kwargs):
    """Returns the current time in H:MM AM/PM format."""
    import datetime
    now = datetime.datetime.now()
    return now.strftime("%I:%M %p")


def search_wikipedia(query):
    """Searches Wikipedia and returns the summary of the first result."""
    from wikipedia import summary

    try:
        # Limit to two sentences for brevity
        return summary(query, sentences=2)
    except Exception as e:
        return f"I couldn't find any information on that. Error: {str(e)}"

# Define the tools that the agent can use
tools = [
    Tool(
        name="Time",
        func=get_current_time,
        description="Useful for when you need to know the current time.",
    ),
    Tool(
        name="Wikipedia",
        func=search_wikipedia,
        description="Useful for when you need to know information about a topic.",
    ),
]

# Load the correct JSON Chat Prompt from the hub
prompt = hub.pull("hwchase17/structured-chat-agent")

# Initialize a ChatOpenAI model
llm = ChatOpenAI(model="gpt-4")

# Memory setup: ConversationBufferWindowMemory stores the conversation history, allowing the agent to maintain context
memory = ConversationBufferWindowMemory(
    memory_key="chat_history",
    return_messages=True,
    k=5  # Specify how many past interactions to keep in memory
)

# Create a structured Chat Agent with tools and memory
agent = create_structured_chat_agent(llm=llm, tools=tools, prompt=prompt)

# AgentExecutor is responsible for managing the interaction between the user input, the agent, and the tools
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    memory=memory,  # Use the conversation memory to maintain context
    handle_parsing_errors=True,  # Handle any parsing errors gracefully
    max_iterations=20,
)

# Initial system message to set the context for the chat
initial_message = (
    "You are an AI assistant that can provide helpful answers using available tools.\n"
    "If you are unable to answer, you can use the following tools: Time and Wikipedia."
)
memory.chat_memory.add_message(SystemMessage(content=initial_message))

@app.route("/")
def index():
    return render_template("chat.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        # Get user input from the HTTP request body
        user_input = request.get_json().get("input")
        if not user_input:
            return jsonify({"error": "No input provided"}), 400
        
        # Add the user's message to the conversation memory
        memory.chat_memory.add_message(HumanMessage(content=user_input))

        # Invoke the agent with the user input and the current chat history
        response = agent_executor.invoke({"input": user_input})

        # Debug: Check the response structure
        print(f"Agent Response: {response}")

        # Ensure the response contains the 'output' key
        if "output" not in response:
            return jsonify({"error": "No output from agent"}), 500

        # Add the agent's response to the conversation memory
        memory.chat_memory.add_message(AIMessage(content=response["output"]))

        # Return the agent's response in the HTTP response
        return jsonify({"response": response["output"]})

    except Exception as e:
        # General error handling
        print(f"Error: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


if __name__ == "__main__":
    # Run the Flask web server
    app.run(host="0.0.0.0", port=8125)

# # Start Chat Loop for interactive conversation
# def run_chat():
#     print("Chatbot is running. Type 'exit' to end the conversation.")
#     while True:
#         user_input = input("User: ")

#         if user_input.lower() == "exit":
#             print("Ending conversation. Goodbye!")
#             break

#         # Add the user's message to the conversation memory
#         memory.chat_memory.add_message(HumanMessage(content=user_input))

#         # Invoke the agent with the user input and the current chat history
#         response = agent_executor.invoke({"input": user_input})
#         print("Bot:", response["output"])

#         # Add the agent's response to the conversation memory
#         memory.chat_memory.add_message(AIMessage(content=response["output"]))

# if __name__ == "__main__":
#     run_chat()
