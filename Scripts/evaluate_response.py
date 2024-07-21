"""
Script para avaliar respostas usando a API OpenAI.
"""
import json
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

def evaluate_response(question, response, text):
    vectorizer = TfidfVectorizer().fit_transform([question, response, text])
    vectors = vectorizer.toarray()
    cosine_sim = cosine_similarity(vectors)
    return {
        "faithfulness": cosine_sim[1][2],
        "answer_relevance": cosine_sim[0][1],
        "context_precision": cosine_sim[1][2],
        "answer_correctness": cosine_sim[0][2],
        "semantic_similarity": cosine_sim[0][1]
    }

if __name__ == "__main__":
    with open('config/openai_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    sample_question = "Qual é a opinião de Carl Sagan sobre a possibilidade de formas de vida baseadas em elementos diferentes do carbono e água?"
    sample_response = "Carl Sagan sugere que é possível que formas de vida possam existir baseadas em elementos diferentes, como o silício, dependendo das condições ambientais."
    chapter_text = "Texto do capítulo relevante do livro Cosmos."
    
    evaluation = evaluate_response(sample_question, sample_response, chapter_text)
    print(evaluation)
