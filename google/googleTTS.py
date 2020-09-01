# -*- coding: utf-8 -*-
"""
Created on Mon Aug 31 11:47:50 2020

@author: Muhammad Abid
"""
import os
import io
import wave
import string
import base64
import random

from gtts import gTTS
from pathlib import Path
from pydub import AudioSegment
from google.cloud import speech_v1p1beta1


class googleTTS():

    def __init__(self):
        self.dir_path = os.path.dirname(os.path.abspath(__file__))
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.dir_path + "/google-credentials.json"
        self.data_dir = self.dir_path + "/data/"

    def text_to_speech(self, text, lang):

        file_nam = self.get_random_string(8)
        file_name = file_nam + '.mp3'
        file_name_wav = file_nam + '.wav'
        file_path = Path(self.data_dir + file_name)

        while file_path.exists():
            file_nam = self.get_random_string(8)
            file_name = file_nam + '.mp3'
            file_name_wav = file_nam + '.wav'
            file_path = Path(self.data_dir + file_name)

        if lang == 'ar':
            lang_code = "ar"
        else:
            lang_code = "en-us"

        tts = gTTS(text=text, lang=lang_code)
        tts.save(str(file_path))

        sound = AudioSegment.from_mp3(str(file_path))
        sound.export(Path(self.data_dir + file_name_wav), format="wav")

        return file_name_wav

    def speech_to_text(self, file_name, lang):

        client = speech_v1p1beta1.SpeechClient()
        file_path = Path(self.data_dir + file_name)
    
        # The language of the supplied audio. Even though additional languages are
        # provided by alternative_language_codes, a primary language is still required.

        if lang == 'ar':
            model = "default"
            channels = 1
            language_code = "ar"
        else:
            model = "phone_call" #"command_and_search"
            channels = 1
            language_code = "en-US"

        config = {"model": model, "encoding": "LINEAR16", "language_code": language_code, "audio_channel_count":channels}
        with io.open(file_path, "rb") as f:
            content = f.read()
        audio = {"content": content}

        response = client.recognize(config, audio)
        returnVal = ""
        for result in response.results:
            # First alternative is the most probable result
            alternative = result.alternatives[0]
            returnVal = alternative.transcript
            #print(u"Transcript: {}".format(alternative.transcript))

        return returnVal

    def save_file(self, audio_type, base64_audio):

        file_nam = self.get_random_string(8)
        file_name = file_nam + '.mp3'
        file_name_wav = file_nam + '.wav'
        file_path = Path(self.data_dir + file_name)

        while file_path.exists():
            file_nam = self.get_random_string(8)
            file_name = file_nam + '.mp3'
            file_name_wav = file_nam + '.wav'
            file_path = Path(self.data_dir + file_name)

        if audio_type == 'mp3':

            base64_data = base64.b64decode(base64_audio)
            #print(base64_data)
            file = open(file_path, 'wb')
            file.write(base64_data)
            file.close()

            sound = AudioSegment.from_mp3(str(file_path))
            sound.export(Path(self.data_dir + file_name_wav), format="wav")
        else:

            base64_data = base64.b64decode(base64_audio)

            file_path = Path(self.data_dir + file_name_wav)
            wf = wave.open(str(file_path), 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(base64_data)
            wf.close()


        return file_name_wav

    def get_base64(self, audio_file):

        file_path = Path(self.data_dir + audio_file)
        with io.open(file_path, "rb") as f:
            content = f.read()

        base64_data = base64.b64encode(content)
        return base64_data.decode("utf-8")

    def get_random_string(self, length):
        letters = string.ascii_lowercase
        result_str = ''.join(random.choice(letters) for i in range(length))
        
        return result_str
