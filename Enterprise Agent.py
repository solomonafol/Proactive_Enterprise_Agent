import streamlit as st
import os
import re
from googleapiclient.discovery import build
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub

# --- 1. Load Secrets (Streamlit Method) ---
# The user will add these in the Streamlit Community Cloud settings
# DO NOT paste your keys here
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
PSE_ID = st.secrets["PSE_ID"]

# Set the GOOGLE_API_KEY as an environment variable for the LLM
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# --- 2. Your Agent Tools (Copied from notebook) ---
# Initialize the Google Custom Search API service
try:
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
except Exception as e:
    st.error(f"Error initializing Google Search API: {e}")
    st.stop()

@tool
def search_google_news(company_name: str, timeframe: str = "d7") -> dict:
    """Searches Google News for a specific company..."""
    # ... (the rest of your function code is identical) ...
    # ... (we'll just use a placeholder for this example) ...
    print(f"--- Calling Tool: search_google_news for '{company_name}' ---")
    try:
        res = service.cse().list(
            q=f'"{company_name}" news',
            cx=PSE_ID,
            num=5,
            dateRestrict=timeframe
        ).execute()
        if 'items' not in res:
            return {"snippets": "No recent news found.", "sources": [], "urls": []}
        items = res.get('items', [])
        snippets = [item.get('snippet', '').replace('\n', '') for item in items]
        sources = [item.get('displayLink', '') for item in items]
        urls = [item.get('link', '') for item in items]
        return {"snippets": snippets, "sources": sources, "urls": urls}
    except Exception as e:
        return {"error": f"Error during news search: {e}"}

@tool
def search_strategic_jobs(company_name: str) -> dict:
    """Searches for high-level (Director, VP, Head of) job postings..."""
    # ... (the rest of your function code is identical) ...
    # ... (we'll just use a placeholder for this example) ...
    print(f"--- Calling Tool: search_strategic_jobs for '{company_name}' ---")
    try:
        query = f'"{company_name}" careers ("Director" OR "VP" OR "Head of" OR "Vice President")'
        res = service.cse().list(q=query, cx=PSE_ID, num=3).execute()
        if 'items' not in res:
            return {"job_titles": "No strategic jobs found.", "snippets": [], "urls": []}
        items = res.get('items', [])
        titles = [item.get('title', '').split('|')[0].strip() for item in items]
        snippets = [item.get('snippet', '').replace('\n', '') for item in items]
        urls = [item.get('link', '') for item in items]
        return {"job_titles": titles, "snippets": snippets, "urls": urls}
    except Exception as e:
        return {"error": f"Error during job search: {e}"}

# --- 3. Your Agent Brain (Copied from notebook) ---
# This part only needs to run once, so we cache it
@st.cache_resource
def get_agent_executor():
    print("Creating new agent executor...")
    tools = [search_google_news, search_strategic_jobs]

    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro", # Using the latest model
        google_api_key=GOOGLE_API_KEY
    )

    # Define the System Prompt
    SYSTEM_PROMPT = """
    You are an expert Enterprise Analyst. Your goal is to provide a concise, actionable intelligence briefing on a target company...
    (Paste your full system prompt here)
    ...
    Question: {input}
    Thought: {agent_scratchpad}
    """

    # Pull the base ReAct prompt template
    react_prompt = hub.pull("hwchase17/react")
    react_prompt.template = SYSTEM_PROMPT

    # Create the Agent
    enterprise_analyst_agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=react_prompt
    )

    # Create the Agent Executor
    agent_executor = AgentExecutor(
        agent=enterprise_analyst_agent,
        tools=tools,
        verbose=True, # Set to False for a cleaner app
        handle_parsing_errors=True
    )
    return agent_executor

# --- 4. The Web App UI (The Streamlit Part) ---

# Set a title for the web app
st.title("🚀 Proactive Enterprise Analyst")
st.markdown("Enter a company name to get an automated intelligence briefing.")

# Get the agent (from cache or create new)
agent_executor = get_agent_executor()

# Create a text input box
user_query = st.text_input("Enter company name (e.g., 'NVIDIA', 'OpenAI'):")

# Create a button
if st.button("Generate Briefing"):
    if user_query:
        # Show a "loading" spinner while the agent works
        with st.spinner("Agent is thinking... (This may take a moment)"):
            try:
                # Run the agent!
                final_response = agent_executor.invoke({
                    "input": f"Give me an intelligence briefing on {user_query}."
                })
                
                # Display the final answer
                st.subheader("Your Intelligence Briefing:")
                st.markdown(final_response['output'])
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a company name.")