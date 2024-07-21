"""
Script para classificar uma consulta usando a API OpenAI.
"""
import json
import openai

def classify_query(query, api_key):
    openai.api_key = api_key
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Classifique a seguinte consulta em um dos capítulos do livro Cosmos: {query}",
        max_tokens=50
    )
    return response.choices[0].text.strip()

if __name__ == "__main__":
    with open('config/openai_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    sample_query = "Qual é a opinião de Carl Sagan sobre a possibilidade de formas de vida baseadas em elementos diferentes do carbono e água?"
    classification = classify_query(sample_query, config['api_key'])
    print(classification)
