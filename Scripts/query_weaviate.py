import weaviate
import json

def query_weaviate(query, weaviate_url):
    client = weaviate.Client(
        url=weaviate_url,
        auth_client_secret=weaviate.AuthApiKey(api_key="YOUR_API_KEY")  # Ajuste conforme necessário
    )
    
    # Query Weaviate
    response = client.query.get("CosmosChapter", ["title", "content", "metadata"]).with_near_text({"concepts": [query]}).do()
    return response

if __name__ == "__main__":
    with open('config/openai_config.json') as f:
        config = json.load(f)
    query = "Qual é a opinião de Carl Sagan sobre a possibilidade de formas de vida baseadas em elementos diferentes do carbono e água?"
    response = query_weaviate(query, 'http://localhost:8080')
    print(response)
