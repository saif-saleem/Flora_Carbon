import os
import re
import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PDFPlumberLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document


def create_faiss_index():
    pdf_dir = "app/data"
    pdf_files = [os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.endswith(".pdf")]

    all_pages = []

    print("🔍 Loading PDF files...")
    for pdf_file in pdf_files:
        try:
            loader = PDFPlumberLoader(pdf_file)
            pages = loader.load()
            for i, page in enumerate(pages):
                page.metadata["source"] = os.path.basename(pdf_file)
                page.metadata["page"] = i + 1
                clause_number = extract_clause_number(page.page_content)
                page.metadata["clause"] = clause_number
            all_pages.extend(pages)
            print(f"✅ Loaded: {pdf_file}")
        except Exception as e:
            print(f"❌ Failed to load {pdf_file}: {e}")

    print("🌐 Scraping Gold Standard websites...")
    web_pages = scrape_gold_standard_websites()
    all_pages.extend(web_pages)

    print("✂️ Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(all_pages)
    print(f"📄 Total chunks: {len(docs)}")

    print("🧠 Generating embeddings...")
    embedding_model = OllamaEmbeddings(model="nomic-embed-text")
    vectorstore = FAISS.from_documents(docs, embedding_model)

    os.makedirs("app/embeddings", exist_ok=True)
    vectorstore.save_local("app/embeddings")
    print("✅ FAISS index created and saved at 'app/embeddings'")


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
            print(f"✅ Scraped content from: {url}")
        except Exception as e:
            print(f"❌ Failed to scrape {url}: {e}")

    return pages


if __name__ == "__main__":
    create_faiss_index()
