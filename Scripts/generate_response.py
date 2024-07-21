import openai
import json

def generate_response(prompt, api_key):
    openai.api_key = api_key
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    return response.choices[0].text.strip()

if __name__ == "__main__":
    with open('config/openai_config.json') as f:
        config = json.load(f)
    prompt = "Explain the possibility of life forms based on elements other than carbon and water."
    response = generate_response(prompt, config['api_key'])
    print(response)
