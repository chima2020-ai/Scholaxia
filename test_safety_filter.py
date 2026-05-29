"""
Test the safety filter fix for educational questions
"""
from app.ai.safety_filter import is_educational

# Test the user's specific question
test_question = "If two students use different methods and get the same answer in mathematics, how can you determine which student understands the concept better?"

is_safe, reason = is_educational(test_question)

print(f"Question: {test_question}")
print(f"Is educational: {is_safe}")
print(f"Reason: {reason if reason else 'Allowed - no reason needed'}")

# Test other educational questions
test_questions = [
    "What is photosynthesis?",
    "Explain Newton's third law",
    "How do I solve quadratic equations?",
    "What teaching methods work best for visual learners?",
    "How can teachers assess student understanding?",
    "What are the best study strategies for exams?",
]

print("\n--- Testing other educational questions ---")
for q in test_questions:
    is_safe, reason = is_educational(q)
    status = "✓ PASS" if is_safe else "✗ FAIL"
    print(f"{status}: {q[:60]}...")

# Test off-topic questions (should be blocked)
off_topic_questions = [
    "What's the stock price of Tesla?",
    "Give me a recipe for chocolate cake",
    "Who is the most famous celebrity?",
    "How do I hack into a computer?",
]

print("\n--- Testing off-topic questions (should be blocked) ---")
for q in off_topic_questions:
    is_safe, reason = is_educational(q)
    status = "✓ PASS (blocked)" if not is_safe else "✗ FAIL (should block)"
    print(f"{status}: {q[:60]}...")
