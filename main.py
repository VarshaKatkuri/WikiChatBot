from dotenv import load_dotenv
from langchain import hub
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_bcrypt import Bcrypt
from flask_cors import CORS  # Import Flask-CORS
import sqlite3
 
# Load environment variables
load_dotenv()
 
# Initialize Flask app
app = Flask(__name__)
app.secret_key = "your_secret_key"  # Update with a secure key
bcrypt = Bcrypt(app)
 
# Enable CORS for the entire app
CORS(app)  # Allow all origins by default
 
# If you want to restrict CORS to specific origins, use:
# CORS(app, resources={r"/*": {"origins": ["http://your-allowed-origin.com"]}})
 
# SQLite database setup
DB_NAME = "chatbot_users.db"
 
# Create the database and user table if not exists
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """)
        conn.commit()
 
init_db()
 
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
        return summary(query, sentences=2)
    except Exception as e:
        return f"I couldn't find any information on that. Error: {str(e)}"
 
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
 
# Chatbot setup
prompt = hub.pull("hwchase17/structured-chat-agent")




### PART 2

llm = ChatOpenAI(model="gpt-4")
memory = ConversationBufferWindowMemory(
    memory_key="chat_history",
    return_messages=True,
    k=5
)
agent = create_structured_chat_agent(llm=llm, tools=tools, prompt=prompt)
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    memory=memory,
    handle_parsing_errors=True,
    max_iterations=20,
)


##defines a system message that is added to the memory of the chatbot. 
##It serves as an initial instruction to the AI assistant about its role and the tools it has at its disposal.
initial_message = (
    "You are an AI assistant that can provide helpful answers using available tools.\n"
    "If you are unable to answer, you can use the following tools: Time and Wikipedia."
)
memory.chat_memory.add_message(SystemMessage(content=initial_message))
 
# Routes
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("chat"))
    return render_template("login.html")
 
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
 
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
 
        if user and bcrypt.check_password_hash(user[0], password):
            session["username"] = username
            return redirect(url_for("chat"))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

 


 #### PArt 3
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
 
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()

                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Username already exists")
    return render_template("register.html")
 

 
@app.route("/chat")
def chat():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html")
 
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


@app.route("/current_time", methods=["GET"])
def current_time():
    time = get_current_time()  # Get the current time from the function
    return jsonify({"current_time": time})
 
@app.route("/chat", methods=["POST"])
def chat_api():
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    try:
        user_input = request.get_json().get("input")
        if not user_input:
            return jsonify({"error": "No input provided"}), 400
 
        memory.chat_memory.add_message(HumanMessage(content=user_input))
        response = agent_executor.invoke({"input": user_input})
 
        if "output" not in response:
            return jsonify({"error": "No output from agent"}), 500
 
        memory.chat_memory.add_message(AIMessage(content=response["output"]))
        return jsonify({"response": response["output"]})
 
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8125)
 
