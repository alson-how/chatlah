from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.models import AskRequest, AskResponse, CrawlRequest, CrawlResponse
from app.retriever import search
from app.indexer import upsert_chunks
from app.chunking import TextChunker
from app.config import OPENAI_API_KEY
from crawler.firecrawl_crawl import FirecrawlClient
import requests
import time

app = FastAPI(title="RAG Site API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Serve the main web interface."""
    return FileResponse("static/index.html")

@app.get("/health")
def health():
    return {"ok": True}

SYSTEM_PROMPT = (
    "You are a company knowledge assistant. "
    "Answer ONLY using the provided context. "
    "If the answer isn't in context, say you don't have that information. "
    "Cite sources by listing their URLs at the end."
)

def call_chat(messages):
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": "gpt-4o-mini", "messages": messages, "temperature": 0.2},
        timeout=120
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    hits = search(req.question, top_k=req.top_k or 6)
    if not hits:
        return AskResponse(answer="I don't have that information in my knowledge base.", sources=[])

    # Compose context
    sources = []
    ctx_lines = []
    for h in hits:
        url = h["meta"]["url"]
        title = h["meta"]["title"]
        text = h["text"]
        ctx_lines.append(f"[{title}] {text}\n(Source: {url})\n")
        sources.append(url)

    user = f"Question: {req.question}\n\nContext:\n" + "\n".join(ctx_lines[:6])
    msg = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user}
    ]
    answer = call_chat(msg)
    return AskResponse(answer=answer, sources=list(dict.fromkeys(sources)))

@app.post("/crawl", response_model=CrawlResponse)
async def crawl(request: CrawlRequest):
    """Crawl a website and index its content."""
    try:
        # Crawl the website
        client = FirecrawlClient()
        pages_data = client.crawl_website(
            url=str(request.target_url),
            max_pages=request.max_pages,
            include_subdomains=request.include_subdomains
        )
        
        if not pages_data:
            raise HTTPException(status_code=400, detail="Failed to crawl any pages from the website")
        
        # Process and index the content
        chunk_processor = TextChunker(chunk_size=1000, chunk_overlap=200)
        total_chunks = 0
        
        for page_data in pages_data:
            try:
                # Process page content into chunks
                chunks = chunk_processor.process_page_content(page_data)
                
                if chunks:
                    # Convert to the format expected by upsert_chunks
                    chunk_data = []
                    for i, chunk in enumerate(chunks):
                        chunk_data.append({
                            "text": chunk['content'],
                            "url": chunk['metadata'].get('url', ''),
                            "title": chunk['metadata'].get('title', 'Untitled'),
                            "chunk_idx": i,
                            "scraped_at": str(time.time())
                        })
                    
                    # Index the chunks
                    upsert_chunks(chunk_data)
                    total_chunks += len(chunk_data)
            except Exception as e:
                print(f"Failed to index page {page_data.get('url', 'unknown')}: {str(e)}")
                continue
        
        return CrawlResponse(
            success=True,
            pages_crawled=len(pages_data),
            chunks_indexed=total_chunks,
            message=f"Successfully crawled {len(pages_data)} pages and indexed {total_chunks} content chunks!"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to crawl website: {str(e)}")

@app.get("/crawled-pages")
async def get_crawled_pages():
    """Get list of crawled pages with statistics."""
    try:
        from app.indexer import collection
        
        # Get all documents with metadata
        results = collection.get(include=['metadatas'])
        
        if not results['metadatas']:
            return []
        
        # Group by URL and collect statistics
        url_data = {}
        for metadata in results['metadatas']:
            url = metadata.get('url', 'Unknown')
            if url != 'Unknown':
                if url not in url_data:
                    url_data[url] = {
                        'count': 0,
                        'title': metadata.get('title', 'Untitled'),
                        'last_crawled': None
                    }
                url_data[url]['count'] += 1
                
                # Get the latest scraped time
                scraped_at = metadata.get('scraped_at')
                if scraped_at:
                    try:
                        scraped_timestamp = float(scraped_at)
                        if not url_data[url]['last_crawled'] or scraped_timestamp > url_data[url]['last_crawled']:
                            url_data[url]['last_crawled'] = scraped_timestamp
                    except (ValueError, TypeError):
                        pass
        
        # Convert to response format
        crawled_pages = []
        for url, data in url_data.items():
            last_crawled = None
            if data['last_crawled']:
                from datetime import datetime
                last_crawled = datetime.fromtimestamp(data['last_crawled']).strftime('%Y-%m-%d %H:%M:%S')
            
            crawled_pages.append({
                "url": url,
                "title": data['title'],
                "chunks_count": data['count'],
                "last_crawled": last_crawled
            })
        
        return crawled_pages
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get crawled pages: {str(e)}")