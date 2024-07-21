import weaviate
import json
import pandas as pd

def ingest_data_to_weaviate(data_path, api_key, weaviate_url):
    client = weaviate.Client(weaviate_url, api_key=api_key)
    
    # Cria um schema no Weaviate se não existir
    class_obj = {
        "class": "CosmosChapter",
        "description": "Chapters from the book Cosmos",
        "properties": [
            {"name": "title", "dataType": ["string"]},
            {"name": "content", "dataType": ["text"]},
            {"name": "metadata", "dataType": ["string"]}
        ]
    }
    client.schema.create_class(class_obj)
    
    # Carrega os dados extraídos
    df = pd.read_csv(data_path)
    for index, row in df.iterrows():
        properties = {
            "title": f"Chapter {index + 1}",
            "content": row["content"],
            "metadata": json.dumps({"chapter": index + 1})
        }
        client.data_object.create(properties, "CosmosChapter")

if __name__ == "__main__":
    with open('config/openai_config.json') as f:
        config = json.load(f)
    ingest_data_to_weaviate('data/extracted_text.csv', config['api_key'], 'http://localhost:8080')
