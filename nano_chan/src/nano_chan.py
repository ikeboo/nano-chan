import subprocess
from threading import Thread
from time import sleep

import yaml

from .voice_capture import VoiceCapture
from .transcriber import Transcriber
from .language_processor import LanguageProcessor
from .voice_generator import VoiceGenerator
from .voice_player import VoicePlayer

class NanoChan:
    '''
    Class to connect and manage modules

    Args:
        config_path(str): path to config file, default: 'configs/config.yaml'

    '''
    def __init__(self,config_path:str='configs/config.yaml'):
        conf = self._load_config(config_path)
        # self._turn_on_jetson_clock()
        self.voice_cap = VoiceCapture(**conf["VoiceCapture"])
        self.transcriber = Transcriber(self.voice_cap.output_q,
                                       **conf["Transcriber"])
        self.lang_processor = LanguageProcessor(self.transcriber.output_q,
                                               **conf["LanguageProcessor"])
        self.voice_gen = VoiceGenerator(self.lang_processor.output_q,
                                        **conf["VoiceGenerator"])
        self.player = VoicePlayer(self.voice_gen.output_q,
                                  **conf["VoicePlayer"])
    
    def _load_config(self,path:str):
        '''load config from yaml file
        Args:
            path(str): path to yaml
        '''
        with open(path,"r",encoding="utf-8") as f:
            conf = yaml.safe_load(f)
        return conf
    
    def _turn_on_jetson_clock(self):
        '''turn on jetson_clocks to unlimit CPU and GPU'''
        try:
            print("Please enter your password to run 'sudo jetson_clocks'")
            subprocess.run(["sudo", "jetson_clocks"], check=True)
            print("Jetson clocks turned on.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to turn on Jetson clocks: {e}")

    def start(self):
        '''start all modules then wait for voice input'''
        self._quit = False
        print("Nano-chan started! Press 'q' to quit.\n")
        flag_thread = Thread(target=self._switch_flag, daemon=True)
        flag_thread.start()

        self.voice_cap.start()
        self.transcriber.start()
        self.lang_processor.start()
        self.voice_gen.start()
        self.player.start()

        while not self._quit:
            text = input()
            if text.lower() == 'q':
                self._quit = True
            if text == 's':
                self._show_state()
        self.close()

    def _switch_flag(self):
        '''toggle voice input availability by audio playing state'''
        while not self._quit:
            
            # while processing or playing
            if (self.player.playing_event.is_set() \
                    or self.lang_processor.processing_event.is_set() \
                    or self.voice_gen.generate_event.is_set()) \
                    and not self.transcriber.locked:  # Eventで状態を取得
                self.transcriber.locked = True
                self.voice_cap.overlap = True
            elif not self.voice_gen.generate_event.is_set() \
                    and not self.lang_processor.processing_event.is_set() \
                    and not self.player.playing_event.is_set() \
                    and self.transcriber.locked:
                self.transcriber.locked = False
                self.voice_cap.overlap = False
                
            # if interrupted
            if self.transcriber.interrupt_event.is_set(): # Interruption in ASR
                
                self.transcriber.interrupt_event.clear()
                
                self.lang_processor.interrupt()
                self.voice_gen.interrupt()
                self.player.interrupt()
                
                while self.lang_processor.processing_event.is_set():
                    sleep(0.05)
                while self.player.playing_event.is_set():
                    sleep(0.05)
                while self.voice_gen.generate_event.is_set():
                    sleep(0.05)

                self.transcriber.locked = False
                self.voice_cap.overlap = False
                print(f"Wait, wait. ", end="",flush=True)
                
            sleep(0.01)

    def _show_state(self):
        '''Show all state for debug'''
        print("- VoiceCapture")
        print(f"{self.voice_cap.recording_event.is_set()=}")
        print(f"{self.voice_cap.output_q.qsize()=}")
        print(f"{self.voice_cap.overlap=}")
        print(f"{self.voice_cap.is_overlap=}")
        print("- Transcriber")
        print(f"{self.transcriber.locked=}")
        print(f"{self.transcriber.interrupt_event.is_set()=}")
        print(f"{self.transcriber.output_q.qsize()=}")
        print(f"{self.transcriber.input_watch_thread.is_alive()=}")
        print("- LanguageProcessor")
        print(f"{self.lang_processor._interrupt=}")
        print(f"{self.lang_processor.processing_event.is_set()=}")
        print(f"{self.lang_processor.output_q.qsize()=}")
        print(f"{self.lang_processor.input_watch_thread.is_alive()=}")
        print("VoiceGenerator")
        print(f"{self.voice_gen._interrupt=}")
        print(f"{self.voice_gen.generate_event.is_set()=}")
        print(f"{self.voice_gen.output_q.qsize()=}")
        print(f"{self.voice_gen.input_watch_thread.is_alive()=}")
        print("- VoicePlayer")
        print(f"{self.player.playing_event.is_set()=}")

    def close(self):
        '''Stop all modules and close app'''
        print('\033[0m'+"\033[36m" + f"\nNano-chan: Bye!"+"\033[0m")
        self.lang_processor.output_q.put("Bye!")  # Stop processing
        sleep(1)
        print("\n",end="")
        self.voice_cap.close()
        print(".",end="")
        self.transcriber.close()
        print(".",end="")
        self.lang_processor.close()
        print(".",end="")
        self.player.close()
        print("Closed")
