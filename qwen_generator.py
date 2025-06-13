import requests
import ast
import re
from dotenv import load_dotenv
import os
from generate_queries import generate_search_queries

load_dotenv()

def generate_instagram_search_queries(topic, location, together_api_key=os.getenv("TOGETHER_API_KEY")):
    url = "https://api.together.xyz/v1/completions"

    headers = {
        "Authorization": f"Bearer {together_api_key}",
        "Content-Type": "application/json"
    }

    prompt = (
        f"Return only a valid Python list of 50 string queries for a Google deep search "
        f"of Instagram accounts about {topic} in {location}, "
        f"using single quotes. Focus on finding Instagram profiles, bloggers, influencers"
        f"pages, or creators. No explanations, no markdown."
    )

    payload = {
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "prompt": prompt,
        "max_tokens": 2048,
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 50,
        "repetition_penalty": 1.1,
        "stop": ["</s>"]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        try:
            raw = response.json()["choices"][0]["text"]
            content_cleaned = re.sub(r"```[\w]*", "", raw).strip()

            try:
                queries = ast.literal_eval(content_cleaned)
                if isinstance(queries, list):
                    return [q for q in queries if isinstance(q, str) and "site:instagram.com" in q]
            except Exception:
                pass

            match = re.search(r"\[.*?\]", content_cleaned, re.DOTALL)
            if match:
                items = match.group(0)
                try:
                    queries = ast.literal_eval(items)
                    return [q for q in queries if isinstance(q, str) and "site:instagram.com" in q]
                except Exception:
                    pass

            lines = content_cleaned.splitlines()
            queries = []
            for line in lines:
                match = re.search(r"'(site:instagram\.com[^']+)'", line)
                if match:
                    queries.append(match.group(1))
            if len(queries) >= 10:
                return queries
        except Exception:
            pass
    else:
        return generate_search_queries(location, topic)