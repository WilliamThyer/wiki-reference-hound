#!/usr/bin/env python3
"""
Test script to compare sequential vs parallel link checking performance.
"""

import time
import argparse
from check_links import check_all_links_with_archives, check_all_links_with_archives_parallel
from utils import format_duration


def test_performance():
    """Test performance difference between sequential and parallel processing."""
    
    # Sample URLs for testing
    test_urls = [
        "https://httpstat.us/200",
        "https://httpstat.us/404", 
        "https://httpstat.us/403",
        "https://httpstat.us/500",
        "https://google.com",
        "https://github.com",
        "https://stackoverflow.com",
        "https://reddit.com",
        "https://wikipedia.org",
        "https://youtube.com",
        "https://httpstat.us/200?sleep=1000",  # Slow response
        "https://httpstat.us/200?sleep=2000",  # Slower response
        "https://httpstat.us/200?sleep=3000",  # Slowest response
    ]
    
    # Test URLs multiple times to get more realistic timing
    links = test_urls * 5  # 65 total links
    
    print("🧪 Performance Test: Sequential vs Parallel Link Checking")
    print("=" * 60)
    print(f"📊 Testing with {len(links)} links")
    print()
    
    # Test 1: Sequential processing
    print("🔄 Testing sequential processing...")
    start_time = time.time()
    
    results_seq = check_all_links_with_archives(
        links, 
        {}, 
        timeout=3.0, 
        delay=0.1
    )
    
    seq_time = time.time() - start_time
    print(f"⏱️  Sequential time: {format_duration(seq_time)}")
    print()
    
    # Test 2: Parallel processing
    print("🚀 Testing parallel processing...")
    start_time = time.time()
    
    results_par = check_all_links_with_archives_parallel(
        links, 
        {}, 
        timeout=3.0,
        max_workers=10,
        chunk_size=50
    )
    
    par_time = time.time() - start_time
    print(f"⏱️  Parallel time: {format_duration(par_time)}")
    print()
    
    # Calculate speedup
    speedup = seq_time / par_time if par_time > 0 else float('inf')
    print("📈 Performance Results:")
    print(f"   Sequential: {format_duration(seq_time)}")
    print(f"   Parallel:   {format_duration(par_time)}")
    print(f"   Speedup:    {speedup:.1f}x faster")
    print()
    
    # Verify results are the same
    seq_alive = sum(1 for _, status, _ in results_seq if status == 'alive')
    par_alive = sum(1 for _, status, _ in results_par if status == 'alive')
    
    print("✅ Results verification:")
    print(f"   Sequential alive links: {seq_alive}")
    print(f"   Parallel alive links:   {par_alive}")
    print(f"   Results match: {'Yes' if seq_alive == par_alive else 'No'}")


def test_different_worker_counts():
    """Test performance with different worker counts."""
    
    test_urls = [
        "https://httpstat.us/200",
        "https://httpstat.us/404",
        "https://httpstat.us/403", 
        "https://google.com",
        "https://github.com",
        "https://stackoverflow.com",
        "https://reddit.com",
        "https://wikipedia.org",
        "https://youtube.com",
    ] * 10  # 90 total links
    
    print("🔧 Testing different worker counts...")
    print("=" * 40)
    
    worker_counts = [1, 5, 10, 20, 50]
    results = {}
    
    for workers in worker_counts:
        print(f"Testing {workers} workers...")
        start_time = time.time()
        
        check_all_links_with_archives_parallel(
            test_urls,
            {},
            timeout=3.0,
            max_workers=workers,
            chunk_size=50
        )
        
        elapsed = time.time() - start_time
        results[workers] = elapsed
        print(f"   Time: {format_duration(elapsed)}")
    
    print("\n📊 Worker Count Performance:")
    print("Workers | Time     | Speedup")
    print("-" * 30)
    
    baseline = results[1]
    for workers in worker_counts:
        speedup = baseline / results[workers] if results[workers] > 0 else float('inf')
        print(f"{workers:7d} | {format_duration(results[workers]):8s} | {speedup:6.1f}x")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test parallel link checking performance')
    parser.add_argument('--workers', action='store_true',
                       help='Test different worker counts')
    
    args = parser.parse_args()
    
    if args.workers:
        test_different_worker_counts()
    else:
        test_performance() 