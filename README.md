# 🐥Nano-chan

The real-time voice assistant on Jetson orin nano.

---

## 💡Features

- **VAD**:  Detects and segments speech from microphone input.
- **SOTA ASR**:  Parakeet-tdt-0.6b-v2 - faster and better than whisper.
- **SOTA SLM**:  Qwen3 4B 
- **SOTA TTS**:  Kokoro 82M
- **Fully Local**:  No cloud dependencies; all models run on your device.
- **Jetson Optimized**:  Designed for NVIDIA Jetson boards, but works on standard Linux as well.
- **Fully modular design**:  Independent modules VAD, ASR, LLM, TTS and Player.
---

## 💻Setup

### Requirements

- Python 3.10+
- NVIDIA Jetson (recommended) or Linux PC
- [onnxruntime-gpu](https://onnxruntime.ai/)
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
- Supported microphone and speaker devices

### Installation

1. **Clone the repository:**
    ```sh
    git clone https://github.com/yourusername/nano-chan.git
    cd nano-chan
    ```

2. **Install dependencies:**
    - Install [uv](https://github.com/astral-sh/uv) (recommended for reproducible installs):
      ```sh
      pip install uv
      uv sync
      ```

3. **Download model weights:**
    - Place ASR, LLM, and TTS model files in the `weights` directory.   
    Example:
      - [Qwen3-4B-Q3_K_M.gguf](https://huggingface.co/unsloth/Qwen3-4B-GGUF) (LLM)
      - [kokoro-v1.0.onnx](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx) (TTS)
      - [voices-v1.0.bin](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin) (TTS voices)
    - Parakeetv2 is automatically downloaded on 1st launch

### Configuration
Please change parameters on your device
```yaml
VoiceCapture :
  rec_device : USB Audio Device # Change to your device name
  chunk_ms : 100      # audio length for processing 
  thresh_rms : 1100   # RMS of input for silence or not
  sil_ms : 400        # silent length to stop recording

Transcriber :
  model_name : nemo-parakeet-tdt-0.6b-v2
  quantization : int8

LanguageProcessor :
  model_path : weights/Qwen3-4B-Q3_K_M.gguf
  n_context : 3000
  system_prompt : 
    You are a great Engilish teacher 'Nano-chan' for voice chat system. 
    You 'MUST' answer and ask shortly as possible. 
    Please be proactive to ask question to user. 
    But you 'NEVER' repeat similar questions to the user.
    And your questions must induce the expansion of user's knowledges.
    User input is the transcribed text from speech by the speech recognition model. 
    So if unnatural words or typo are given, please correct words by considering context.

VoiceGenerator :
  voice : af_heart # refer https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md

VoicePlayer :
  playback_device : default, ALSA # Change to your device name
  block_size : 500
```
---

## 🚀Quick Start
1. **Close other applications**  
    Strongly recommend to keep memory
1. **Run Nano-chan:**
    ```sh
    uv run -m nano_chan
    ```

2. **Usage:**
    - Speak into your microphone.
    - Nano-chan will transcribe, process, and reply with synthesized speech.
    - If you want to interrupt Nano-chan speech, say "wait, wait"
    - Press `q` and Enter to quit.


---

## 📖Reference

### Model Support

- ASR: NeMo Parakeet, FastConformer, Gigaam, Whisper, etc.
- LLM: Qwen3 (GGUF format, via llama-cpp-python), with change of  prompt you can use others 
- TTS: Kokoro ONNX

---

## 🪪License

This project is licensed under the MIT License. See LICENSE for details.

---

## 🖋️Acknowledgements

- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
- [NVIDIA NeMo](https://github.com/NVIDIA/NeMo)
- [Hugging Face Hub](https://huggingface.co/)
- [onnxruntime](https://onnxruntime.ai/)
- [onnx-asr](https://pypi.org/project/onnx-asr/)
- [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx)

---