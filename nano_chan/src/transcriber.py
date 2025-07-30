from threading import Thread, Event
from queue import Queue
from nano_chan.libs import onnx_asr

class Transcriber:
    '''
    Module to transcribe the voice audio to text.

    Args:
        input_q (Queue): Queue to hold audio clips for transcription.
        model_name (str): Name of the ONNX model to use for transcription.
        quantization (str): Quantization type for the model.
        sample_rate (int): Sample rate of the audio clips.
    '''
    def __init__(self, input_q:Queue, 
                 model_name="nemo-parakeet-tdt-0.6b-v2", 
                 quantization="int8",
                 sample_rate=48000):

        self.input_q = input_q
        self.model = onnx_asr.load_model(model_name, quantization=quantization)
        self.sample_rate = sample_rate
        
        self.output_q = Queue() # Queue to hold transcribed text

        self.locked = False
        self.interrupt_event = Event()
    
    def start(self):
        self.is_running = True
        self.input_watch_thread = Thread(target=self._watch_queue, daemon=True)
        self.input_watch_thread.start()
      
    def _watch_queue(self):
        
        while self.is_running:
            sent_text = ""
            is_overlap,audio = self.input_q.get()
            # stop flag
            if audio is None:
                break
            text = self.model.recognize(audio,sample_rate=self.sample_rate)
            if self.locked or is_overlap:
                # detect interruption
                if text and text.lower().count("wait") >= 2:
                    self.interrupt_event.set()
                    self._flush_queue()
                    continue
            elif not self.locked and not is_overlap:
                if text is None or text.strip() == "":
                    pass
                else:
                    sent_text += text.strip() + " "
                
                # put data if recording stop
                if sent_text.strip() != "":
                    self.output_q.put(sent_text)

    def _flush_queue(self):
        try:
            while not self.input_q.empty():
                self.input_q.get_nowait()
        except Exception:
            pass
        try:
            while not self.output_q.empty():
                self.output_q.get_nowait()
        except Exception:
            pass
    def close(self):
        self.is_running = False
        self.output_q.put(None)
        self.input_watch_thread.join()
        del self.model
