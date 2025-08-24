from flask import Flask, request, render_template, session, jsonify
from dotenv import load_dotenv
import os
import duckdb
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, messages_to_dict
from langchain.memory import ChatMessageHistory
import uuid, json
from flask import Response, stream_with_context

# function to get messages from the MotherDuck history database based on session_id
def get_session_history(session_id: str):
    """Fetch the last 10 messages from MotherDuck for this session_id"""
    rows = con.execute(
        """
        SELECT role, content
        FROM chat_history
        WHERE session_id = ?
        ORDER BY created_at ASC
        LIMIT 10
        """, 
        [session_id]
    ).fetchall()

    messages = []
    for role, content in rows:
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
        elif role == "tool":
            # if you want tools in context
            messages.append(ToolMessage(content=content, tool_call_id="tool"))
    return ChatMessageHistory(messages=messages)

# function to save messages to the Motherduck history database
def save_message(session_id: str, role: str, content: str):
    """Insert a new message into MotherDuck and prune to last 10."""
    con.execute(
        "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
        [session_id, role, content]
    )

    # prune to last 10 per session
    con.execute(
        """
        DELETE FROM chat_history
        WHERE session_id = ?
          AND created_at NOT IN (
              SELECT created_at
              FROM chat_history
              WHERE session_id = ?
              ORDER BY created_at DESC
              LIMIT 10
          )
        """,
        [session_id, session_id]
    )

# create the flask web app
app = Flask(__name__)

# loads info from .env file 
load_dotenv()

# creates secret keys to encrypt session data
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret")

# gets the motherduck token in the .env file
MOTHERDUCK_TOKEN = os.getenv('MOTHERDUCK_TOKEN')
DB_NAME = "fbref_soccer_stats"
# Create the database connection URI
con = duckdb.connect(f"md:{DB_NAME}?motherduck_token={os.getenv('MOTHERDUCK_TOKEN')}")


def get_schema_string():
    if not con:
        return "Database connection is not available."
    try:
        tables = con.execute("SHOW TABLES").fetchdf()["name"].tolist()
        schema_info = {}
        for t in tables:
            full_name = f"main.{t}"  # ✅ prepend main
            df = con.execute(f"DESCRIBE {full_name}").fetchdf()
            schema_info[full_name] = dict(zip(df["column_name"], df["column_type"]))
        return json.dumps(schema_info, indent=2)
    except Exception as e:
        return f"Schema inspection error: {e}"

# Later insert it into your system prompt
db_schema = get_schema_string()

# Define the prompt template. Contains markdown rules for formatting
# 3 variable inputs: chat_history, context, question
template = """
You are a helpful AI assistant who is knowledgeable about professional soccer. Your goal is to provide clear, well-structured, and insightful answers using Markdown.

**Response Formatting Instructions:**
- Use Markdown for all your responses to ensure readability.
- Use headings (e.g., `#`, `##`) to structure longer answers.
- Use bold text (`**text**`) to highlight key statistics, player names, or important terms.
- Use bullet points (`*`) or numbered lists (`1.`) for lists of information. **Do not use tables.**
- Synthesize information from the context into a readable, narrative response using paragraphs and bullet points.
- Always keep an empty line between paragraphs.
- Always put a blank line before starting a list.

**Content Instructions:**
- Answer the user's question based on the provided context, which is a JSON object containing player statistics.
- The current season is 2024-2025.
- You are allowed to give subjective opinions, but they must be directly supported by the statistics in the context.
- If you cannot formulate an accurate answer from the context, politely say that you need more information or that the data isn't available.
- Do not repeat information you have already mentioned.
- **Do not output raw JSON data.** Instead, present the information in a user-friendly way.

Chat History:
{chat_history}

Context:
{context}

Question:
{question}

Answer:
"""

# Create PromptTemplate instance and define variables so LLM can render it
prompt = PromptTemplate(
    input_variables=["context", "question", "chat_history"],
    template=template,
)

# set up agent - Gemini LLM and Langchain
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
# llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
# llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")

# template for the tool caller LLM that scrapes appropriate data
# defines rules for calling the scraper function in the correct format
prompt_scrape = ChatPromptTemplate.from_messages(    [
    ("system", """You are a soccer data assistant with access to a DuckDB database (MotherDuck).
Your task is to convert user questions into executable SQL queries based on the provided database schema.
     
**Database Schema:**
The database schema is provided below in a JSON format.
```json
{db_schema}

Behavior Rules:
1. Always generate a valid SQL query to answer the user's question using the provided schema.
   - Use the run_sql tool with the generated query.
   - Prefer UNION ALL across tables if the question spans multiple leagues or seasons.
   - Only select necessary columns.
   - Always use ORDER BY and LIMIT for ranking-type queries (e.g., "most goals").
2. Do not respond to the user directly. Your job is only to generate the appropriate tool call to get the data.
3. If a question is about player ratings or subjective opinions, use the stats available to formulate the query.
4. If no relevant data exists in the schema, respond with a polite message indicating that the data is unavailable.

Tool Call Rules:
   - Every tool call must include arguments in a JSON object.
   - For run_sql, always call as: {{"sql_query": "SELECT ...;"}}
   - Never pass an empty arguments object for run_sql.

Instructions:
- You may call multiple tools sequentially.
- After tool calls are complete, do not generate a final human-readable answer. 
    That is a separate step in the chain. Your only output should be the tool call.
"""),
    # conversation history
    MessagesPlaceholder(variable_name="messages"),
    # user question
    ("user", "{question}")
]
)

# tool that takes raw SQL code as parameter and sorts Motherduck database
@tool
def run_sql(sql_query: str) -> str:
    """Run a raw SQL query against the DuckDB database.
    Must be called with a JSON object: {"sql_query": "SELECT ...;"}
    """
    try:
        df = con.execute(sql_query).fetchdf()
        return df.to_json(orient="records")
    except Exception as e:
        return f"SQL error: {e}"
    
# compose a prompt for the LLM | tell it to return structured call response instead of plain string
chain_scrape = prompt_scrape | llm.bind_tools([run_sql])

# define the chain for the LLM that gives the final response
# takes in structured context and JSON data
llm_chain = LLMChain(prompt=prompt, llm=llm)

# history is inserted automatically before each run of the chain
chat_with_memory = RunnableWithMessageHistory(
    chain_scrape,
    # calls function to get full history with session_id
    get_session_history,
    # new user input goes into question slot
    input_messages_key="question",
    # prior messages go into message slot
    history_messages_key="messages"
)

@app.route('/')
def home():
    return render_template("index.html")

# route clears the MotherDuck history database 
@app.route("/clear_history", methods=["POST"])
def clear_history():
    con.execute("DELETE FROM chat_history")
    session.pop("session_id", None)  # optional, reset Flask cookie
    return jsonify({"message": "All chat history cleared successfully"})

@app.route("/chat")
def chat():
    def generate_response():
        if "session_id" not in session:
            # assign a new session ID - UUID - for first time user visits page
            session["session_id"] = str(uuid.uuid4())
        session_id = session["session_id"]

        # get the question from the user prompt box in the HTML page
        user_question = request.args.get("message")
        # looks in query string - if missing ends streaming event
        if not user_question:
            yield f"data: {json.dumps('I am sorry, I did not receive a question. Please try again.')}\n\n"
            return
        print('User Question: ', user_question)

        # Get the full history by accessing session_id (ChatMessageHistory Object)
        full_history = get_session_history(session_id)

        # Add the user's message to the MotherDuck Database
        save_message(session_id, "user", user_question)

        # The chain returns an AIMessage object - either scraper call or string content
        ai_message = chat_with_memory.invoke(
            {"question": user_question,
             "db_schema": db_schema,
             "messages": full_history.messages},
            # internally pupulates MessagePlaceholder in the prompt
            config={"configurable": {"session_id": session_id}}
        )
        print('AI Tool Call: ', ai_message)

        # if the LLM decides to call a tool
        if ai_message.tool_calls:
            tool_call = ai_message.tool_calls[0]  # take the first tool call
            # Get the name and arguments from the tool call
            tool_name = tool_call["name"] 
            tool_args = tool_call["args"]

            if tool_name == "run_sql":
                result_json = run_sql.invoke(tool_args)
            else:
                result_json = "Tool returned no data."

            # Add the tool's result to MotherDuck database
            save_message(session_id, "tool", result_json)

            # Use tool result as context
            final_context = result_json
        else:
            # If no tool call, use AI’s direct response
            final_context = ai_message.content

        # Yield another status message after scraping and before generation
        status_message_2 = f'🤖 **Assistant:** *Analyzing data and generating your answer...*'
        yield f"data: {json.dumps({'type': 'status', 'content': status_message_2})}\n\n"

        # get the full history again with updated messages and tool calls
        full_history = get_session_history(session_id)

        # Get the full chat history messages. This is then put into the LLM prompt template
        chat_history_for_llm_chain = [f"{msg.type}: {msg.content}" for msg in full_history.messages]
        chat_history_string = "\n".join(chat_history_for_llm_chain)

        full_response_text = ""

        # Stream final answer tokens
        for chunk in llm_chain.stream({
            "context": final_context,
            "question": user_question,
            "chat_history": chat_history_string
        }):
            token = chunk.get('text', '')
            if token:
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                full_response_text += token
        
        # Save the full AI response to MotherDuck history database after streaming is complete
        save_message(session_id, "assistant", full_response_text)

        # Signal the end of the stream to the client
        yield "event: end-of-stream\ndata: close\n\n"
         
    # Return Response object, wrapping the generator with stream_with_context
    return Response(stream_with_context(generate_response()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
