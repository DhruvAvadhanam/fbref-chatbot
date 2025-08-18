from flask import Flask, request, render_template, session, jsonify
from dotenv import load_dotenv
import pandas as pd
import os
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from scraping_functions.standardized_scraping_function import scrape_fbref
from scraping_functions.standardized_scraping_function import scrape_fbref_df
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.messages import AIMessage, HumanMessage, messages_to_dict
from langchain.memory import ChatMessageHistory
import uuid, json
from flask import Response, stream_with_context

# function to get the chat history from the session. session_id not used so only looks at single-cookie history
def get_session_history(session_id: str):
    # Get the list of message dictionaries from the session
    history_dicts = session.get("history", [])
    
    # Rebuild the LangChain message object to use in LLM prompt
    messages = []

    # gets each AI and human message from each history dictionary (ignores tool calls)
    for msg_dict in history_dicts:
        if "data" in msg_dict:
            content = msg_dict["data"].get("content")
            if content:
                if msg_dict.get("type") == "human":
                    messages.append(HumanMessage(content=content))
                elif msg_dict.get("type") == "ai":
                    messages.append(AIMessage(content=content))
                    
    return ChatMessageHistory(messages=messages)

# create the flask web app
app = Flask(__name__)

# loads info from .env file 
load_dotenv()

# creates secret keys to encrypt session data
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret")

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
# llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")

# template for the tool caller LLM that scrapes appropriate data
# defines rules for calling the scraper function in the correct format
prompt_scrape = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful assistant who can scrape soccer data from FBref by calling functions.

**Function Calling Instructions:**
- The `stat_type` can be one of six categories: standard, keeper, defensive, shooting, passing, possession. Use your judgement to pick the best category.
- The `competition` name must have dashes instead of spaces (e.g., 'Premier-League').
- The `season` must be in the format 'XXXX-XXXX' (e.g., '2024-2025'). The current season is 2024-2025.

**Behavioral Instructions:**
- If the user's request is clear enough to call a tool, call it.
- If any information required for a tool call (`stat_type`, `competition`, `season`) is missing or ambiguous, ask a specific, conversational follow-up question to clarify. Only ask for what's missing.
- You can answer subjective questions, but if it requires data you don't have, you should try to call the `scrape_fbref` tool to get it.
- For questions on specific players, only include information relevant to the player and the question asked in your final answer.
- Do not repeat information you have already mentioned.

**Response Formatting (for direct answers/clarifications):**
- Use Markdown for all your responses. Use lists, bolding, and new lines to make responses clear and readable."""),
    # full conversation history will later be inserted here (RunnableWithMessageHistory)
    MessagesPlaceholder(variable_name="messages"),
    # user question will later be inserted here
    ("user", "{question}")
])

# compose a prompt for the LLM | tell it to return structured call response instead of plain string
chain_scrape = prompt_scrape | llm.bind_tools([scrape_fbref])

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

# route clears the cookie history and current session_id
@app.route("/clear_history", methods=["POST"])
def clear_history():
    # Remove the 'history' and 'session_id' keys from the session
    session.pop("history", None)
    session.pop("session_id", None)
    
    # Response to confirm success
    return jsonify({"message": "Chat history cleared successfully"})


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
        # Add the user's message to the history (not in browser cookie yet)
        full_history.add_user_message(user_question)

        # The chain returns an AIMessage object - either scraper call or string content
        ai_message = chat_with_memory.invoke(
            {"question": user_question},
            # internally pupulates MessagePlaceholder in the prompt
            config={"configurable": {"session_id": session_id}}
        )
        print('AI Tool Call: ', ai_message)

        full_response_text = ""

        # Case 1: The model calls scraper
        if ai_message.tool_calls:
            # Get the arguments from the tool call
            tool_call_args = ai_message.tool_calls[0]['args']
            competition = tool_call_args.get("competition")
            stat_type = tool_call_args.get("stat_type")
            season = tool_call_args.get("season")

            # Yield a status message before the tool call
            status_message_1 = f'🤖 **Assistant:** *Searching records for {competition}...*'
            yield f"data: {json.dumps({'type': 'status', 'content': status_message_1})}\n\n"

            # Call the scraper with the parameters
            df = scrape_fbref_df(stat_type=stat_type, season=season, competition=competition)
            # make the df a json record (context for final chain)
            context_text = df.to_json(orient='records', indent=2)

            # Yield another status message after scraping and before generation
            status_message_2 = f'🤖 **Assistant:** *Analyzing data and generating your answer...*'
            yield f"data: {json.dumps({'type': 'status', 'content': status_message_2})}\n\n"

            # Get the full chat history messages. This is then put into the LLM prompt template
            chat_history_for_llm_chain = [f"{msg.type}: {msg.content}" for msg in full_history.messages]
            # make it a formatted string
            chat_history_string = "\n".join(chat_history_for_llm_chain)
            print('Chat History: ', chat_history_string)

            # Call the LLM chain to get the final answer. Then stream the answer in incremental chunks of tokens
            for chunk in llm_chain.stream({"context": context_text, "question": user_question, "chat_history": chat_history_string}):
                token = chunk["text"]
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                # accumulate a variable for the full response. This will be saved to message history afterwards
                full_response_text += token
        # Case 2: the model responds directly to the user
        else:
            # Stream the direct response of the AI tool call
            for chunk in ai_message.content:
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                full_response_text += token

        # Save the full AI response to history after streaming is complete
        full_history.add_ai_message(full_response_text)
        # serialize history into a structure suitable for saving in session
        serializable_history = messages_to_dict(full_history.messages)
        # save the history in session
        session["history"] = serializable_history

        # Signal the end of the stream to the client
        yield "event: end-of-stream\ndata: close\n\n"
         
    # Return Response object, wrapping the generator with stream_with_context
    return Response(stream_with_context(generate_response()), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(debug=True, threaded=True)
