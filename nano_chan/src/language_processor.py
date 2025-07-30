from threading import Thread, Event,Lock
from typing import List,Dict
from queue import Queue,Empty
import re

from llama_cpp import Llama

class LanguageProcessor:
    def __init__(self, input_q:Queue, 
                 system_prompt:str,
                 model_path:str="weights/Qwen3-4B-Q3_K_M.gguf",# Qwen3-4B-Q3_K_M.gguf
                 n_context:int=3200): 
        '''
        Args:
            input_q(Queue) : queue contains user input text
            system_prompt(str) : prompt text as system prompt
            model_path(str) : path to gguf model file
            n_context(int) : length of context
        '''
        self.input_q = input_q
        self.system_prompt = system_prompt
        self._interrupt = False
        self.lock = Lock()
        self.messages = self._init_messages()
        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=-1,
            verbose=False,
            n_ctx=n_context,
        )
        self.max_tokens = int(n_context*0.7)  # 余裕を持たせる

        self.output_q = Queue() # queue to put generated text
        self.processing_event = Event() # set if generating 
    
    def start(self)->None:
        '''start waiting input text'''
        self.is_running = True
        self.input_watch_thread = Thread(target=self._watch_queue, daemon=True)
        self.input_watch_thread.start()
        
    def _init_messages(self):
        '''set system prompt'''
        return [
            {"role": "system", 
             "content": self.system_prompt}
        ]
    
    def _count_tokens(self, messages:List[Dict]):
        '''count tokens in context'''
        total = 0
        for msg in messages:
            # システムプロンプトも含めてカウント
            total += len(self.llm.tokenize(msg["content"].encode('utf-8')))
        return total

    def _watch_queue(self):

        while self.is_running:
            self.processing_event.clear()

            # get text from transcriber and display
            print("\033[33m" + f"You      : ", end="",flush=True)
                
            text = self.input_q.get()
            if self._interrupt:
                self._interrupt=False

            self.processing_event.set()

            if text is None:
                self.processing_event.clear()
                break
            cur_ctxt_len = self._count_tokens(self.messages)
            print(text + '\033[0m\n',flush=True)

            # clear history if requested
            if text.strip().strip(".").lower() in ["clear","reset"]:
                self.messages= self._init_messages()
                print("Cleared conversation history")
                # self.processing_event.clear()
                continue

            # prepare prompt
            # トークン数がMAX_TOKENSを超えたら古いメッセージを削除
            while cur_ctxt_len > self.max_tokens and len(self.messages) > 1:
                # システムプロンプト（最初の1件）は残す
                self.messages.pop(1)
                assert self.messages[0]["role"] == "system"
            self.messages.append({"role": "user", "content": text+" /no_think"})
            
            
            # initialize
            print("\033[36m" + f"Nano-chan: ", end="",flush=True)
            assistant_response = "" # 回答全文
            sent_response = "" # 送信済み
            think_end = False

            for chunk in self.llm.create_chat_completion(
                messages=self.messages,
                max_tokens=256,
                temperature=0.7,
                stop=["<|endoftext|>", "<|im_end|>"],
                stream=True  # ストリーミングモードを有効にする
                ):
                if self._interrupt:
                    break
                if 'choices' in chunk and len(chunk['choices']) > 0:
                    assistant_response_chunk = chunk['choices'][0]['delta'].get('content', '')
                    assistant_response += assistant_response_chunk
                    # assistant_response = assistant_response.strip()
                    # detect end of think
                    if not think_end:
                        if len(assistant_response)>0  and not "<think>" in assistant_response:
                            '''in case think mode doesn't start properly'''
                            think_end = True
                        if "</think>\n\n" in assistant_response:
                            think_end = True
                            assistant_response = ""
                            continue
                        if len(assistant_response)>25:
                            print(assistant_response.replace("<think>\n\n",""), end='',flush=True)
                            think_end = True

                    # after think end
                    if think_end:
                        print(assistant_response_chunk, end='',flush=True)
                
                        if len(assistant_response)>0 and \
                            (assistant_response[-1] in ['.', '!', '?',",",'\n']\
                              or "<|im_end|>" in assistant_response \
                            or "<|endoftext|>" in assistant_response):
                            section = self._remove_emoji(assistant_response).replace("*","").replace(sent_response,"").replace("<think>\n\n","")
                            if assistant_response[-1] =="," and len(section) < 5:
                                continue
                            if section.strip() != "":
                                self.output_q.put(section)
                                sent_response += section

            if self._interrupt:
                print('\033[0m\n')
                self._interrupt = False
                self.processing_event.clear()
                continue
            # submit remaining response
            section = self._remove_emoji(assistant_response).replace("*","").replace(sent_response,"").replace("<think>\n\n","")
            if len(section) > 1: # discard empty or single character responses
                self.output_q.put(section)
            # アシスタントの回答も履歴に追加
            self.messages.append({"role": "assistant", "content": self._remove_emoji(assistant_response).replace("<think>\n\n</think>\n\n","")})
            print('\033[0m\n')

    def interrupt(self)->None:
        '''stop generating answer and flush output queue'''
        self._interrupt = True
        self._flush_queue()
        self.processing_event.clear()  

    def _flush_queue(self):
        with self.lock:
            while True:
                try:
                    self.output_q.get_nowait()
                except Empty:
                    break

    def close(self)->None:
        '''stop generating and close'''
        self.is_running = False
        self.output_q.put(None)
        self.input_watch_thread.join()
        del self.llm

    @staticmethod
    def _remove_emoji(text):
            text = text[:]
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # emoticons
                "\U0001F300-\U0001F5FF"  # symbols & pictographs
                "\U0001F680-\U0001F6FF"  # transport & map symbols
                "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                "\U00002700-\U000027BF"  # Dingbats
                "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
                "\U00002600-\U000026FF"  # Misc symbols
                "\U00002B50-\U00002B55"
                "\U0000231A-\U0000231B"
                "\U00002500-\U00002BEF"
                "\U0001F700-\U0001F77F"
                "\U0001F780-\U0001F7FF"
                "\U0001F800-\U0001F8FF"
                "\U0001FA70-\U0001FAFF"
                "\U0001F018-\U0001F270"
                "\U0001F650-\U0001F67F"
                "]+",
                flags=re.UNICODE
            )
            return emoji_pattern.sub(r'', text)

