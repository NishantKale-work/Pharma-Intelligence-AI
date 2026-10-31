
from app.llm.llm_client import generate_response

prompt = """
You are a pharmaceutical market intelligence assistant.

In two sentences, explain why market growth data
is useful when comparing pharmaceutical markets.
"""

try:
    answer = generate_response(prompt)

    print("\n--- LLM RESPONSE ---")
    print(answer)

except Exception as error:
    print("LLM test failed:", error)
