from flask import Flask, request, render_template, session, jsonify
from dotenv import load_dotenv
import pandas as pd
import os
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from scraping_functions.standardized_scraping_function import scrape_fbref
from scraping_functions.standardized_scraping_function import scrape_fbref_df
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputKeyToolsParser
from langchain_core.runnables import RunnableWithMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import AIMessage, HumanMessage, messages_to_dict
from langchain.memory import ChatMessageHistory
import uuid
from flask_cors import CORS

def get_session_history(session_id: str):
    # Get the list of message dictionaries from the session
    history_dicts = session.get("history", [])
    
    # Recreate the ChatMessageHistory object
    messages = []

    for msg_dict in history_dicts:
        if "data" in msg_dict:
            content = msg_dict["data"].get("content")
            if content:
                if msg_dict.get("type") == "human":
                    messages.append(HumanMessage(content=content))
                elif msg_dict.get("type") == "ai":
                    messages.append(AIMessage(content=content))
                    
    return ChatMessageHistory(messages=messages)

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret")

load_dotenv()

# Define the prompt template
template = """
You are a helpful AI assistant who is knowledgeable about professional soccer.
Please format your responses using Markdown notation to make them as easily readable as possible.
Always put a blank line before starting a numbered or bulleted list in Markdown.
Answer the user's question based on the provided tabular data context.
The current season is 2024/2025.
You are allowed to give subjective opinions, as long as they are backed up by statistics.
If asked a subjective question, use relevant data from the context to back up your claims as best as you can.
If you still cannot formulate an accurate answer based on the context, politely say that you need more information.
Do not repeat previous info you have already mentioned.

Chat History:
{chat_history}

Context:
{context}

Question:
{question}

Answer:
"""

# Create PromptTemplate instance
prompt = PromptTemplate(
    input_variables=["context", "question", "chat_history"],
    template=template,
)

# set up agent - LLM and Langchain
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
# llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")

tools = [scrape_fbref]

prompt_scrape = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant who can scrape soccer data from FBref by calling functions."
    "Please format your responses using Markdown notation to make them as easily readable as possible."
    "The stat_type can be one of six categories: standard, keeper, defensive, shooting, passing, possession. Use your judgement to pick the best category."
    "When gathering the competition, it must follow the rule that any spaces between words will contain a dash. Here is an example: Premier-League"
    "When gathering the season, it must follow the format XXXX-XXXX. Here is an example: 2024-2025."
    "The current season is 2024/2025."
    "Please also answer subjective questions. If asked a subjective question, use relevant data from the context to back up your claims as best as you can."
    # "If any information for a tool call, like competition, season, or stat_type, is missing from the current question, use the **Chat History** to find the correct information. Do not ask for it again if it has already been provided."
    "If anything is missing or ambiguous, ask a specific, conversational follow-up question to clarify."
    "Only ask for what's missing. Do not repeat previous info you have already mentioned."
    "For questions on specific players, only include information relevant to the player and the question asked"),
    MessagesPlaceholder(variable_name="messages"),
    ("user", "{question}")
])

chain_scrape = prompt_scrape | llm.bind_tools([scrape_fbref])

llm_chain = LLMChain(prompt=prompt, llm=llm)

# set up message memory
chat_with_memory = RunnableWithMessageHistory(
    chain_scrape,
    get_session_history,
    input_messages_key="question",
    history_messages_key="messages"
)

@app.route('/')
def home():
    return render_template("index.html")

@app.route("/clear_history", methods=["POST"])
def clear_history():
    # Remove the 'history' and 'session_id' keys from the session
    session.pop("history", None)
    session.pop("session_id", None)
    
    # Response to confirm success
    return jsonify({"message": "Chat history cleared successfully"})


@app.route("/chat", methods=["POST"])
def chat():

    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    session_id = session["session_id"]

    # get the question from the input box
    data = request.get_json()
    user_question = data.get("message")
    print('User Question: ', user_question)

    # Get the full history of the session
    full_history = get_session_history(session_id)
    # Add the user's message
    full_history.add_user_message(user_question)

    # The chain returns an AIMessage object
    ai_message = chat_with_memory.invoke(
        {"question": user_question},
        config={"configurable": {"session_id": session_id}}
    )
    print('AI Tool Call: ', ai_message)

    # Case 1: The model calls scraper
    if ai_message.tool_calls:
        # Get the arguments
        tool_call_args = ai_message.tool_calls[0]['args']
        competition = tool_call_args.get("competition")
        stat_type = tool_call_args.get("stat_type")
        season = tool_call_args.get("season")

        # Call the scraper
        df = scrape_fbref_df(stat_type=stat_type, season=season, competition=competition)
        context_text = df.to_string(index=False)

        # Get the full chat history messages for the prompt
        chat_history_for_llm_chain = [f"{msg.type}: {msg.content}" for msg in full_history.messages]
        chat_history_string = "\n".join(chat_history_for_llm_chain)
        print('Chat History: ', chat_history_string)

        # Get the final answer
        answer = llm_chain.invoke({"context": context_text, "question": user_question, "chat_history": chat_history_string})["text"]
        print('Response: ', answer)

        full_history.add_ai_message(answer)
    else:
        answer = ai_message.content
        full_history.add_ai_message(answer)

    # save the updated history
    serializable_history = messages_to_dict(full_history.messages)
    session["history"] = serializable_history

            
    return jsonify({
        "reply": answer
    })


if __name__ == '__main__':
    app.run(debug=True)
