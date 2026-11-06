from openai import OpenAI
from finnie.config import get_settings

def ask_model(prompt: str) -> str :

    #load the environment parameters
    settings = get_settings()

    #initialize the OpenAI client
    client = OpenAI()

    response = client.responses.create(
        model=settings["model"],
        input=prompt,
    )
    return response.output_text