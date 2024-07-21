"""
Script para gerar embeddings usando a API OpenAI.
"""
import json
import openai

def generate_embeddings(text, api_key):
    openai.api_key = api_key
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=[text]  # Lista com o texto
    )
    return response['data'][0]['embedding']

if __name__ == "__main__":
    with open('config/openai_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    text = "Carl Sagan discute a possibilidade de vida baseada em elementos diferentes do carbono e da água."
    embeddings = generate_embeddings(text, config['api_key'])
    print(embeddings)
