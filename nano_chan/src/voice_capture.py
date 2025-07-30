from collections import deque
import queue
from threading import Thread,Event
import time

import sounddevice as sd 
import numpy as np

class VoiceCapture:
    '''Capture voice, trim silence, queue clips for processing.

    Attribute:
        recording_event: Event to indicate recording is in progress.
        output_q: Queue to hold audio clips.
    
    Args:
        rec_device (str):   Recording device name.
        fs (int):           Sampling frequency.
        chunk_ms (int):     Chunk size in milliseconds.
        thresh_rms (int):   RMS threshold for voice detection. 0-32768.
        tail_ms (int):      Tail length in milliseconds to trim silence.
        sil_ms (int):       Silence length in milliseconds to detect end of recording.
        pre_frames (int):   Number of frames to keep before recording starts.
        min_clip_len_sec (float): Minimum clip length in seconds to queue.
    '''
    def __init__(self, 
                 rec_device='USB Audio Device',
                 fs=48000, 
                 chunk_ms=100, 
                 thresh_rms=1100, 
                 tail_ms=70, 
                 sil_ms=400,
                 pre_frames=5,
                 min_clip_len_sec=0.8):

        self.FS = fs
        self.CHUNK_MS = chunk_ms
        self.THRESH_RMS = thresh_rms
        self.TAIL_MS = tail_ms
        self.SIL_MS = sil_ms
        self.PRE_FRAMES = pre_frames
        self.MIN_CLIP_LEN_SEC = min_clip_len_sec
        self.chunk = int(self.FS * self.CHUNK_MS / 1000)
        self.sil_chunks = int(self.SIL_MS / self.CHUNK_MS)
        self.tail_chunks = int(self.TAIL_MS / self.CHUNK_MS)
        self.output_q = queue.Queue()
        self.in_dev = sd.query_devices(rec_device, 'input')['index']

        # flags
        self.recording_event = Event() # set active if recording
        self.overlap = False           # flag changed by mediator
        self.is_overlap = False        # state when recording starts

    def start(self):
        '''start capture audio and put data'''
        self.is_running = True
        self._thread = Thread(target=self._capture, daemon=True)
        self._thread.start()
        
    @staticmethod
    def _rms(frame: np.ndarray) -> float:
        return np.sqrt(np.mean(frame.astype(np.float32)**2))

    def _capture(self):
        buf, silent = [], 0
        pre_buf = deque(maxlen=self.PRE_FRAMES)   # ring buffer,always keep recent chunks
        tail_buf = []
        tailing = False
        def cb(indata, frames, time_info, status):
            '''
            indata(np.ndarray): wavedata with chunk length
            '''
            nonlocal buf, silent, tail_buf, tailing, pre_buf
            if status:
                print(status, flush=True)

            val = self._rms(indata)

            # update recent chunks
            pre_buf.append(indata.copy())         

            if val > self.THRESH_RMS:
                if not buf:                       # recording starts
                    self.recording_event.set()
                    self.is_overlap = bool(self.overlap) # copy
                    buf.extend(pre_buf)           # already contains current chunk
                else:
                    buf.append(indata.copy())     # normal in‑recording append
                silent = 0
                tail_buf.clear()
                tailing = False

            elif buf:
                if not tailing:
                    silent += 1
                    if silent >= self.sil_chunks:   # possible end
                        tailing = True
                if tailing:
                    tail_buf.append(indata.copy())
                    if len(tail_buf) >= self.tail_chunks:
                        audio = np.concatenate(buf + tail_buf, axis=0)
                        if audio.size > self.MIN_CLIP_LEN_SEC * self.FS:
                            self.output_q.put((self.is_overlap, audio.squeeze()))
                        # reset everything, including pre‑buffer
                        buf, silent, tail_buf, tailing = [], 0, [], False
                        pre_buf.clear()
                        self.recording_event.clear()
                else:
                    buf.append(indata.copy())

        with sd.InputStream(device=self.in_dev, channels=1,
                            samplerate=self.FS, blocksize=self.chunk,
                            dtype='int16', callback=cb):
            while self.is_running: 
                time.sleep(0.1)
                
    def close(self):
        self.is_running = False
        self.output_q.put((None,None))
        self._thread.join()



