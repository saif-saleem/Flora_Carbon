from langchain_community.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from collections import Counter
import re
from dotenv import load_dotenv
import os

load_dotenv()

EMBEDDING_DIR = "app/embeddings"
embedding_model = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

db = FAISS.load_local(
    EMBEDDING_DIR,
    embedding_model,
    allow_dangerous_deserialization=True
)

target_keywords = [
    "validation timeline", "validation period", "validation deadline",
    "validation shall be completed", "validation must be completed",
    "validation must occur", "validation shall occur",
    "validation timing", "validation requirements", "validation is required to be completed",
    "validation is required within", "validation shall be conducted within",
    "validation prior to certification", "validation prior to verification",
    "verification timeline", "verification period", "verification deadline",
    "verification shall be completed", "verification must be completed",
    "verification must occur", "verification shall occur",
    "verification timing", "verification requirements", "verification is required to be completed",
    "verification is required within", "verification shall be conducted within",
    "certification timeline", "certification period", "certification deadline"
]

def retrieve_context(query: str, k: int = 40):
    docs = db.similarity_search(query, k=k)
    context_text = "\n\n".join([doc.page_content for doc in docs])

    quoted_sentences = []
    for doc in docs:
        sentences = re.split(r'(?<=[.!?]) +', doc.page_content)
        for sentence in sentences:
            if any(keyword.lower() in sentence.lower() for keyword in target_keywords):
                quoted_sentences.append({
                    "source": doc.metadata.get("source", "Unknown"),
                    "clause": doc.metadata.get("clause", f"Page {doc.metadata.get('page', 'N/A')}"),
                    "snippet": sentence.strip().replace("\n", " ")
                })

    quoted_sentences = quoted_sentences[:10]

    source_counts = Counter()
    for doc in docs:
        source = doc.metadata.get("source", "Unknown")
        source_counts[source] += 1

    total = sum(source_counts.values())
    significant_sources = [
        {"source": src, "clause": doc.metadata.get("clause", f"Page {doc.metadata.get('page', 'N/A')}")}
        for src, count in source_counts.items()
        if (count / total) >= 0.5
        for doc in docs if doc.metadata.get("source") == src
    ]

    return context_text, significant_sources, quoted_sentences

def build_prompt(query, context, quoted_sentences):
    quoted_section = "\n\n".join(
        f"- From `{qs['source']}`, Clause `{qs['clause']}`: \"{qs['snippet']}\""
        for qs in quoted_sentences
    )

    template = '''You are an expert assistant specialized in carbon credit standards, methodologies, and certifications.

Use the provided CONTEXT and QUOTED SENTENCES to answer the user's question with maximum accuracy.

**Instructions:**
1. Provide a clear and direct answer.
2. Explicitly cite the documents and clauses to support your answer.
3. If any QUOTED SENTENCE contains information about Validation or Verification timing (even indirectly), include it clearly in the answer.
4. Do not say "no explicit fixed deadline" if there is any sentence mentioning timing, period, or requirement for Validation or Verification.
5. If truly no such sentence is present, then state: "The information is not available in the provided documents."

CONTEXT:
{context}

QUOTED SENTENCES:
{quoted_section}

QUESTION:
{question}

ANSWER (Direct + Detailed + Quoted):'''

    prompt = PromptTemplate(
        input_variables=["context", "quoted_section", "question"],
        template=template
    )
    return prompt.format(context=context, quoted_section=quoted_section, question=query)

def needs_clarification(query):
    standards = ["vcs", "gs", "cdm"]
    if any(std in query.lower() for std in standards):
        return None
    general_topics = ["arr project", "validation requirement", "methodology"]
    if any(term in query.lower() for term in general_topics):
        return "Do you want the validation requirements according to a specific Carbon Standard (e.g., VCS, GS, CDM)?"
    return None

def summarize_answer(answer):
    sentences = re.split(r'(?<=[.!?]) +', answer)
    return sentences[0] if sentences else answer
