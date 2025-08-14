#!/usr/bin/env python3
"""
Complete pipeline script for crawling, chunking, and indexing website content.
Usage: python scripts/run_pipeline.py [URL]
"""

import os
import sys
import argparse
from typing import Optional
import time

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from crawler.firecrawl_crawl import FirecrawlClient
from app.indexer import ContentIndexer


def run_crawling_pipeline(
    target_url: str,
    max_pages: int = 10,
    include_subdomains: bool = False,
    clear_existing: bool = False
):
    """Run the complete crawling and indexing pipeline."""
    print("=" * 60)
    print("RAG System - Website Crawling & Indexing Pipeline")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Step 1: Validate configuration
        print("\n1. Validating configuration...")
        
        if not settings.firecrawl_api_key:
            print("❌ ERROR: FIRECRAWL_API_KEY environment variable not set!")
            print("Please set your Firecrawl API key in the environment or .env file.")
            return False
        
        print(f"✅ Firecrawl API key configured")
        print(f"✅ Target URL: {target_url}")
        print(f"✅ Max pages: {max_pages}")
        print(f"✅ Include subdomains: {include_subdomains}")
        print(f"✅ Chroma DB path: {settings.chroma_db_path}")
        
        # Step 2: Initialize components
        print("\n2. Initializing components...")
        
        try:
            crawler = FirecrawlClient(api_key=settings.firecrawl_api_key)
            print("✅ Firecrawl client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Firecrawl client: {str(e)}")
            return False
        
        try:
            indexer = ContentIndexer()
            print("✅ Content indexer initialized")
        except Exception as e:
            print(f"❌ Failed to initialize content indexer: {str(e)}")
            return False
        
        # Step 3: Validate API connection
        print("\n3. Validating API connection...")
        
        if not crawler.validate_api_key():
            print("❌ Failed to validate Firecrawl API key!")
            print("Please check your API key and internet connection.")
            return False
        
        print("✅ Firecrawl API key validated")
        
        # Step 4: Clear existing data if requested
        if clear_existing:
            print("\n4. Clearing existing indexed data...")
            if indexer.clear_collection():
                print("✅ Existing data cleared")
            else:
                print("⚠️  Warning: Failed to clear existing data")
        
        # Step 5: Crawl website
        print(f"\n5. Crawling website: {target_url}")
        print("This may take a few minutes depending on the site size...")
        
        try:
            pages = crawler.crawl_website(
                url=target_url,
                max_pages=max_pages,
                include_subdomains=include_subdomains
            )
            
            if not pages:
                print("❌ No pages were crawled successfully!")
                return False
            
            print(f"✅ Successfully crawled {len(pages)} pages")
            
            # Display sample of crawled pages
            print("\n📄 Crawled pages sample:")
            for i, page in enumerate(pages[:5], 1):
                title = page.get('title', 'Untitled')[:50]
                url = page.get('url', '')[:60]
                content_length = len(page.get('content', ''))
                print(f"   {i}. {title} ({url}) - {content_length} chars")
            
            if len(pages) > 5:
                print(f"   ... and {len(pages) - 5} more pages")
        
        except Exception as e:
            print(f"❌ Crawling failed: {str(e)}")
            return False
        
        # Step 6: Index content
        print(f"\n6. Indexing content into Chroma database...")
        print("Processing and generating embeddings...")
        
        try:
            indexing_result = indexer.index_multiple_pages(pages)
            
            print(f"✅ Indexing completed!")
            print(f"   📊 Pages processed: {indexing_result['pages_successful']}/{indexing_result['pages_total']}")
            print(f"   📊 Pages failed: {indexing_result['pages_failed']}")
            print(f"   📊 Total chunks created: {indexing_result['chunks_processed']}")
            print(f"   📊 Total chunks indexed: {indexing_result['chunks_indexed']}")
            
            if indexing_result['pages_failed'] > 0:
                print(f"⚠️  Warning: {indexing_result['pages_failed']} pages failed to index")
        
        except Exception as e:
            print(f"❌ Indexing failed: {str(e)}")
            return False
        
        # Step 7: Verify indexing
        print("\n7. Verifying indexing...")
        
        try:
            stats = indexer.get_collection_stats()
            print(f"✅ Verification successful!")
            print(f"   📊 Total documents in database: {stats['total_documents']}")
            print(f"   📊 Collection name: {stats['collection_name']}")
            print(f"   📊 Embedding model: {stats['embedding_model']}")
        
        except Exception as e:
            print(f"❌ Verification failed: {str(e)}")
            return False
        
        # Step 8: Test search functionality
        print("\n8. Testing search functionality...")
        
        try:
            test_query = "main features"
            test_results = indexer.search_similar_content(test_query, n_results=3)
            
            if test_results:
                print(f"✅ Search test successful!")
                print(f"   🔍 Test query: '{test_query}'")
                print(f"   📊 Results found: {len(test_results)}")
                
                # Show top result
                if test_results:
                    top_result = test_results[0]
                    print(f"   📄 Top result: {top_result['metadata'].get('title', 'Untitled')}")
                    print(f"   🎯 Similarity score: {top_result['similarity_score']:.3f}")
            else:
                print("⚠️  Search test returned no results (this might be normal)")
        
        except Exception as e:
            print(f"⚠️  Search test failed: {str(e)}")
        
        # Summary
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"⏱️  Total time: {elapsed_time:.1f} seconds")
        print(f"🌐 Website: {target_url}")
        print(f"📊 Pages indexed: {indexing_result['pages_successful']}")
        print(f"📊 Chunks created: {indexing_result['chunks_indexed']}")
        print(f"💾 Database: {settings.chroma_db_path}")
        print("\n🚀 Your RAG system is ready!")
        print(f"   • Start the API server: python app/api.py")
        print(f"   • Test the health endpoint: GET http://localhost:5000/health")
        print(f"   • Ask questions: POST http://localhost:5000/ask")
        print()
        
        return True
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Pipeline failed with unexpected error: {str(e)}")
        return False


def main():
    """Main function to run the pipeline."""
    parser = argparse.ArgumentParser(
        description="RAG System - Website Crawling & Indexing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/run_pipeline.py https://docs.python.org
    python scripts/run_pipeline.py https://example.com --max-pages 20 --include-subdomains
    python scripts/run_pipeline.py https://example.com --clear-existing
        """
    )
    
    parser.add_argument(
        "url",
        nargs="?",
        default=settings.target_website,
        help="Website URL to crawl (default: TARGET_WEBSITE env var)"
    )
    
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Maximum number of pages to crawl (default: 10)"
    )
    
    parser.add_argument(
        "--include-subdomains",
        action="store_true",
        help="Include subdomains in crawling"
    )
    
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Clear existing indexed data before crawling"
    )
    
    args = parser.parse_args()
    
    # Validate URL
    if not args.url:
        print("❌ ERROR: No URL provided!")
        print("Either provide URL as argument or set TARGET_WEBSITE environment variable.")
        print("\nUsage: python scripts/run_pipeline.py <URL>")
        sys.exit(1)
    
    # Ensure URL has protocol
    if not args.url.startswith(('http://', 'https://')):
        args.url = 'https://' + args.url
    
    # Run the pipeline
    success = run_crawling_pipeline(
        target_url=args.url,
        max_pages=args.max_pages,
        include_subdomains=args.include_subdomains,
        clear_existing=args.clear_existing
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
