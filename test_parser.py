#!/usr/bin/env python3
import logging
from parallel_simple_parser import ParallelSimpleParser
import parser_rules as rules

# Configure logging
logging.basicConfig(
    level=getattr(logging, rules.LOGGING["level"]),
    format=rules.LOGGING["format"]
)

if __name__ == "__main__":
    # Initialize parser with a test query
    parser = ParallelSimpleParser("python programming")
    
    # Run the parser with default settings from rules
    parser.run()
    
    # Or you can specify custom settings (they will be validated against security limits)
    # parser.run(num_browsers=4, pages_per_browser=5)