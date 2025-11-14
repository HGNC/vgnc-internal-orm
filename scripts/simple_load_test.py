#!/usr/bin/env python3
"""
Load testing script for VGNC Internal ORM.

This script performs load testing on the VGNC ORM system by simulating
multiple concurrent users performing database lookup operations.
It supports different test types and generates detailed performance reports.

Usage:
    python simple_load_test.py --test lookup --users 10 --duration 60 --output results.json
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import threading
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from vgnc_internal_orm.config.settings import get_settings
from vgnc_internal_orm.sessions.factory import SessionFactory
from vgnc_internal_orm.models.species import Species
from vgnc_internal_orm.models.genefam import Genefam
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing."""

    # Test configuration
    test_type: str
    users: int
    duration_seconds: int
    start_time: str
    end_time: str

    # Performance metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    errors: List[str] = None

    # Timing metrics
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    avg_response_time: float = 0.0

    # Concurrency metrics
    peak_concurrent_users: int = 0
    requests_per_second: float = 0.0

    # Database-specific metrics
    db_connections_created: int = 0
    db_query_time_total: float = 0.0

    def __post_init__(self):
        """Initialize list fields."""
        if self.errors is None:
            self.errors = []

    def calculate_derived_metrics(self):
        """Calculate derived metrics from collected data."""
        if self.successful_requests > 0:
            self.avg_response_time = self.total_response_time / self.successful_requests

        # Calculate actual duration
        start_dt = datetime.fromisoformat(self.start_time)
        end_dt = datetime.fromisoformat(self.end_time)
        actual_duration = (end_dt - start_dt).total_seconds()

        if actual_duration > 0:
            self.requests_per_second = self.total_requests / actual_duration


class LoadTestWorker:
    """Worker thread for executing load test operations."""

    def __init__(self, worker_id: int, test_config: Dict[str, Any]):
        self.worker_id = worker_id
        self.test_config = test_config
        self.metrics = LoadTestMetrics(
            test_type=test_config['test_type'],
            users=test_config['users'],
            duration_seconds=test_config['duration'],
            start_time=datetime.now().isoformat(),
            end_time=""
        )

    def run_test(self, duration_seconds: int) -> LoadTestMetrics:
        """Execute load test operations for the specified duration."""
        start_time = time.time()
        end_time = start_time + duration_seconds

        # Initialize database connection
        settings = get_settings()
        session_factory = SessionFactory(settings.database)

        try:
            while time.time() < end_time:
                operation_start = time.time()

                try:
                    # Perform database operation based on test type
                    if self.test_config['test_type'] == 'lookup':
                        self._perform_lookup_test(session_factory)
                    else:
                        raise ValueError(f"Unsupported test type: {self.test_config['test_type']}")

                    operation_time = time.time() - operation_start

                    # Update metrics
                    self.metrics.total_requests += 1
                    self.metrics.successful_requests += 1
                    self.metrics.total_response_time += operation_time
                    self.metrics.min_response_time = min(self.metrics.min_response_time, operation_time)
                    self.metrics.max_response_time = max(self.metrics.max_response_time, operation_time)

                except Exception as e:
                    self.metrics.total_requests += 1
                    self.metrics.failed_requests += 1
                    error_msg = f"Worker {self.worker_id}: {str(e)}"
                    self.metrics.errors.append(error_msg)
                    logger.warning(error_msg)

                # Small delay to prevent overwhelming the database
                time.sleep(0.01)

        finally:
            self.metrics.end_time = datetime.now().isoformat()
            self.metrics.calculate_derived_metrics()

        return self.metrics

    def _perform_lookup_test(self, session_factory: SessionFactory):
        """Perform species lookup operations."""
        with session_factory.get_session() as session:
            # Mix of different lookup operations to simulate realistic usage
            operations = [
                self._lookup_random_species,
                self._lookup_species_by_status,
                self._lookup_all_species_limit,
                self._lookup_species_with_relationships,
            ]

            # Choose operation randomly (simplified - in real implementation use random.choice)
            operation_idx = self.metrics.total_requests % len(operations)
            operations[operation_idx](session)

    def _lookup_random_species(self, session: Session):
        """Lookup a random species by taxon_id."""
        # Use some common test taxon IDs that should exist
        test_taxon_ids = [9000, 9001, 9002, 9606, 10090]  # Model organisms + human + mouse
        taxon_id = test_taxon_ids[self.metrics.total_requests % len(test_taxon_ids)]

        species = session.query(Species).filter_by(taxon_id=taxon_id).first()
        # Access the result to ensure the query is executed
        if species:
            _ = species.display_name

    def _lookup_species_by_status(self, session: Session):
        """Lookup species by their live status."""
        from vgnc_internal_orm.models.species import SpeciesLiveStatus

        species = session.query(Species).filter(
            Species.is_live == SpeciesLiveStatus.YES
        ).limit(10).all()

        # Access results to ensure query execution
        for s in species[:3]:  # Access first few results
            _ = s.genefam_prefix

    def _lookup_all_species_limit(self, session: Session):
        """Lookup all species with a limit."""
        species = session.query(Species).limit(20).all()

        # Access results to ensure query execution
        for s in species[:5]:  # Access first few results
            _ = s.taxon_id

    def _lookup_species_with_relationships(self, session: Session):
        """Lookup species and access their relationships."""
        species = session.query(Species).filter_by(taxon_id=9000).first()

        if species:
            # This will trigger relationship loading
            chromosomes = species.get_active_chromosomes(session)
            _ = len(chromosomes)


def run_load_test(test_type: str, users: int, duration: int, output_file: str) -> Dict[str, Any]:
    """Run a load test with the specified parameters."""
    print(f"Starting load test: {test_type} with {users} users for {duration} seconds")

    test_config = {
        'test_type': test_type,
        'users': users,
        'duration': duration,
    }

    # Start load test
    start_time = datetime.now()

    # Create and run worker threads
    with ThreadPoolExecutor(max_workers=users) as executor:
        # Submit worker tasks
        futures = []
        for i in range(users):
            worker = LoadTestWorker(i + 1, test_config)
            future = executor.submit(worker.run_test, duration)
            futures.append(future)

        # Collect results from all workers
        worker_metrics = []
        for future in as_completed(futures):
            try:
                metrics = future.result()
                worker_metrics.append(metrics)
                print(f"Worker completed: {metrics.total_requests} requests")
            except Exception as e:
                print(f"Worker failed: {e}")
                logger.error(f"Worker failed: {traceback.format_exc()}")

    end_time = datetime.now()

    # Aggregate metrics from all workers
    aggregated_metrics = aggregate_worker_metrics(worker_metrics, test_config, start_time, end_time)

    # Save results to output file
    with open(output_file, 'w') as f:
        json.dump(aggregated_metrics, f, indent=2)

    print(f"Load test completed. Results saved to: {output_file}")
    return aggregated_metrics


def aggregate_worker_metrics(worker_metrics: List[LoadTestMetrics],
                           test_config: Dict[str, Any],
                           start_time: datetime,
                           end_time: datetime) -> Dict[str, Any]:
    """Aggregate metrics from all worker threads."""

    if not worker_metrics:
        return {}

    # Aggregate basic metrics
    total_requests = sum(m.total_requests for m in worker_metrics)
    successful_requests = sum(m.successful_requests for m in worker_metrics)
    failed_requests = sum(m.failed_requests for m in worker_metrics)

    total_response_time = sum(m.total_response_time for m in worker_metrics)
    min_response_time = min(m.min_response_time for m in worker_metrics if m.min_response_time != float('inf'))
    max_response_time = max(m.max_response_time for m in worker_metrics)

    # Aggregate all errors
    all_errors = []
    for m in worker_metrics:
        all_errors.extend(m.errors)

    # Calculate actual test duration
    actual_duration = (end_time - start_time).total_seconds()

    # Create aggregated result
    result = {
        'test_summary': {
            'test_type': test_config['test_type'],
            'configured_users': test_config['users'],
            'configured_duration_seconds': test_config['duration'],
            'actual_duration_seconds': round(actual_duration, 2),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'worker_count': len(worker_metrics),
        },
        'performance_metrics': {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate_percent': round((successful_requests / total_requests) * 100, 2) if total_requests > 0 else 0,
            'requests_per_second': round(total_requests / actual_duration, 2) if actual_duration > 0 else 0,
            'avg_response_time_ms': round((total_response_time / successful_requests) * 1000, 2) if successful_requests > 0 else 0,
            'min_response_time_ms': round(min_response_time * 1000, 2),
            'max_response_time_ms': round(max_response_time * 1000, 2),
        },
        'errors': {
            'total_errors': len(all_errors),
            'error_details': all_errors[:20],  # Limit to first 20 errors to avoid huge files
        },
        'worker_breakdown': [
            {
                'worker_id': i + 1,
                'total_requests': m.total_requests,
                'successful_requests': m.successful_requests,
                'failed_requests': m.failed_requests,
                'avg_response_time_ms': round(m.avg_response_time * 1000, 2) if m.avg_response_time > 0 else 0,
            }
            for i, m in enumerate(worker_metrics)
        ]
    }

    return result


def main():
    """Main entry point for the load testing script."""
    parser = argparse.ArgumentParser(
        description='Load testing script for VGNC Internal ORM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Run lookup test with 5 users for 30 seconds
  python simple_load_test.py --test lookup --users 5 --duration 30 --output light-load.json

  # Run lookup test with 20 users for 60 seconds
  python simple_load_test.py --test lookup --users 20 --duration 60 --output medium-load.json

  # Run lookup test with 50 users for 30 seconds
  python simple_load_test.py --test lookup --users 50 --duration 30 --output heavy-load.json
        '''
    )

    parser.add_argument(
        '--test',
        required=True,
        choices=['lookup'],
        help='Type of test to run'
    )

    parser.add_argument(
        '--users',
        type=int,
        required=True,
        help='Number of concurrent users to simulate'
    )

    parser.add_argument(
        '--duration',
        type=int,
        required=True,
        help='Test duration in seconds'
    )

    parser.add_argument(
        '--output',
        required=True,
        help='Output JSON file for results'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.users <= 0:
        print("Error: --users must be a positive integer")
        sys.exit(1)

    if args.duration <= 0:
        print("Error: --duration must be a positive integer")
        sys.exit(1)

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Run the load test
        results = run_load_test(args.test, args.users, args.duration, args.output)

        # Print summary
        print("\nLoad Test Summary:")
        print(f"  Total Requests: {results['performance_metrics']['total_requests']}")
        print(f"  Success Rate: {results['performance_metrics']['success_rate_percent']}%")
        print(f"  Requests/Second: {results['performance_metrics']['requests_per_second']}")
        print(f"  Avg Response Time: {results['performance_metrics']['avg_response_time_ms']}ms")
        print(f"  Total Errors: {results['errors']['total_errors']}")

        # Exit with error code if there were failures
        if results['errors']['total_errors'] > 0:
            print(f"\nWarning: {results['errors']['total_errors']} errors occurred during the test")
            sys.exit(1)
        else:
            print("\nLoad test completed successfully!")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\nLoad test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nLoad test failed: {e}")
        logger.error(f"Load test failed: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == '__main__':
    main()