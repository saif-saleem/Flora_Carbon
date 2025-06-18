import os
from openai import OpenAI
from app.utils import retrieve_context, build_prompt, needs_clarification
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chat_state = {}

def get_answer(query, model="gpt-4.1", follow_up_answer=None):
    if follow_up_answer:
        query = f"{chat_state.get('original_query', '')} ({follow_up_answer})"
        context, sources, quoted_sentences = retrieve_context(query)
        prompt = build_prompt(chat_state.get('original_query', ''), context, quoted_sentences)
    else:
        clarification = needs_clarification(query)
        if clarification:
            chat_state["original_query"] = query
            return None, None, clarification

        chat_state["original_query"] = query
        context, sources, quoted_sentences = retrieve_context(query)
        prompt = build_prompt(query, context, quoted_sentences)

    response = openai_client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert assistant specialized in carbon credit standards, methodologies, and certifications."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.0
    )

    answer = response.choices[0].message.content.strip()
    return answer, sources, None

def reset_chat():
    global chat_state
    chat_state = {}
