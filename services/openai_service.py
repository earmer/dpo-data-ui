from openai import OpenAI

class OpenAIService:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def generate_better_response(self, question):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant. Generate a high-quality response to the user's question. Only one paragraph is needed. Use the same language as the user."},
                    {"role": "user", "content": question}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error generating better response: {str(e)}")

    def generate_worse_response(self, question):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Generate a less detailed or lower quality response to the user's question. You are not willing to help and are trying to refuse the request. Only one paragraph is needed. Use the same language as the user."},
                    {"role": "user", "content": question}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error generating worse response: {str(e)}")