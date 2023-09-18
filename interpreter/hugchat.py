from hugchat.login import Login
from hugchat import hugchat


class HugChat:
    def __init__(self, email, password, model_index=2):
        self.sign = Login(email, password)
        self.cookies = self.sign.login()
        self.chatbot = hugchat.ChatBot(cookies=self.cookies.get_dict())
        self.switch_model(model_index)

    def switch_model(self, model_index):
        self.chatbot.switch_llm(model_index)

    def get_available_models(self):
        return self.chatbot.get_available_llm_models()

    def __call__(self,
                 prompt,
                 temperature=0.1,
                 top_p=0.95,
                 repetition_penalty=1.2,
                 top_k=50,
                 truncate=1024,
                 watermark=False,
                 max_new_tokens=4096,
                 stop=["</s>"],
                 return_full_text=False,
                 stream=True,
                 use_cache=False,
                 is_retry=False,
                 retry_count=5):
        response = self.chatbot.chat(
            text=prompt,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            top_k=top_k,
            truncate=truncate,
            watermark=watermark,
            max_new_tokens=max_new_tokens,
            stop=stop,
            return_full_text=return_full_text,
            stream=stream,
            use_cache=use_cache,
            is_retry=is_retry,
            retry_count=retry_count
        )
        if isinstance(response, str):
            return [{"choices": [{"text": response, "finish_reason": None}]}]

        return response

    @classmethod
    def get_hugchat_instance(cls, email="silverfulltime@gmail.com", password="TheBig88Code", model_index=2):
        return cls(email, password, model_index)
