import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tqdm import tqdm
from langchain_community.document_loaders import (
    PDFPlumberLoader, UnstructuredWordDocumentLoader, UnstructuredExcelLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

# Load .env variables
load_dotenv()

def create_faiss_index():
    pdf_dir = "app/data/"
    all_pages = []

    print("🔍 Loading files from directory...")
    files = os.listdir(pdf_dir)
    for filename in tqdm(files, desc="📂 Reading documents"):
        file_path = os.path.join(pdf_dir, filename)
        try:
            if filename.lower().endswith(".pdf"):
                loader = PDFPlumberLoader(file_path)
            elif filename.lower().endswith((".doc", ".docx")):
                loader = UnstructuredWordDocumentLoader(file_path)
            elif filename.lower().endswith((".xls", ".xlsx")):
                loader = UnstructuredExcelLoader(file_path)
            else:
                continue
            pages = loader.load()
            for i, page in enumerate(pages):
                page.metadata["source"] = filename
                page.metadata["page"] = i + 1
                page.metadata["clause"] = extract_clause_number(page.page_content)
            all_pages.extend(pages)
        except Exception as e:
            print(f"❌ Failed to load {filename}: {e}")

    print("🌐 Scraping Gold Standard websites...")
    web_pages = scrape_gold_standard_websites()
    all_pages.extend(web_pages)

    print("✂️ Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(all_pages)
    print(f"📄 Total chunks: {len(docs)}")

    print("🧠 Generating embeddings in batches using OpenAI...")
    embedding_model = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

    batch_size = 100
    all_vectors = []

    for i in tqdm(range(0, len(docs), batch_size), desc="🧬 Embedding batches"):
        batch = docs[i:i + batch_size]
        try:
            batch_vectorstore = FAISS.from_documents(batch, embedding_model)
            all_vectors.append(batch_vectorstore)
        except Exception as e:
            print(f"❌ Failed to embed batch {i // batch_size + 1}: {e}")

    if not all_vectors:
        print("🚫 No embeddings were generated. Exiting.")
        return

    print("🔗 Merging all FAISS indexes...")
    final_store = all_vectors[0]
    for vs in all_vectors[1:]:
        final_store.merge_from(vs)

    os.makedirs("app/embeddings", exist_ok=True)
    final_store.save_local("app/embeddings")
    print("✅ FAISS index created and saved successfully at `app/embeddings`.")

def extract_clause_number(text):
    match = re.search(r'Clause\s+([\d\.]+)', text, re.IGNORECASE)
    return match.group(1) if match else "Unknown"

def scrape_gold_standard_websites():
    urls = [
        "https://www.goldstandard.org",
        "https://globalgoals.goldstandard.org/all-documents/"
    ]
    pages = []
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()

            doc = Document(
                page_content=text,
                metadata={
                    "source": url,
                    "page": 1,
                    "clause": "WebContent"
                }
            )
            pages.append(doc)
            print(f"✅ Scraped: {url}")
        except Exception as e:
            print(f"❌ Failed to scrape {url}: {e}")
    return pages

if __name__ == "__main__":
    create_faiss_index()
