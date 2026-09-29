"""
Prime Number Calculator (1 to 100)
This script finds and displays all prime numbers between 1 and 100.
"""

import sys
from typing import List


def is_prime(n: int) -> bool:
    """Check if a given integer n is a prime number."""
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    
    # Check divisors up to sqrt(n)
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def find_primes_in_range(start: int, end: int) -> List[int]:
    """Find all prime numbers in the inclusive range [start, end]."""
    if start > end:
        raise ValueError(f"Start value ({start}) cannot be greater than end value ({end}).")
    
    return [num for num in range(start, end + 1) if is_prime(num)]


def main() -> None:
    """Main execution function."""
    try:
        start_val = 1
        end_val = 100
        primes = find_primes_in_range(start_val, end_val)
        
        print("=" * 50)
        print(f"Prime Number Search Results [{start_val} ~ {end_val}]")
        print("=" * 50)
        print(f"Total primes found: {len(primes)}")
        print("Prime numbers list:")
        print(primes)
        print("=" * 50)
    except Exception as e:
        print(f"Error occurred during execution: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
