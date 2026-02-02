# Welcome to Opsis Code Editor

## A Python Sample File

def fibonacci(n):
    """Generate Fibonacci sequence up to n terms"""
    fib_sequence = []
    a, b = 0, 1
    for _ in range(n):
        fib_sequence.append(a)
        a, b = b, a + b
    return fib_sequence

def is_prime(num):
    """Check if a number is prime"""
    if num < 2:
        return False
    for i in range(2, int(num ** 0.5) + 1):
        if num % i == 0:
            return False
    return True

# Main execution
print("=" * 50)
print("Welcome to Opsis Code Editor - Python Demo")
print("=" * 50)

# Test Fibonacci
print("\nFibonacci Sequence (first 10 terms):")
fib_nums = fibonacci(10)
print(fib_nums)

# Test Prime numbers
print("\nPrime numbers between 1 and 30:")
primes = [num for num in range(1, 31) if is_prime(num)]
print(primes)

# List comprehension example
print("\nSquares of numbers 1-10:")
squares = [x**2 for x in range(1, 11)]
print(squares)

# Dictionary example
editor_info = {
    "name": "Opsis Code Editor",
    "version": "1.0.0",
    "language": "Python",
    "supported_formats": ["py", "js", "java", "ts", "html", "css"]
}

print("\nEditor Information:")
for key, value in editor_info.items():
    print(f"  {key}: {value}")

print("\n" + "=" * 50)
print("Code execution completed successfully!")
print("=" * 50)
