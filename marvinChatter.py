# -*- coding: utf-8 -*-
"""
Created on Mon Aug 31 11:47:50 2020

@author: Muhammad Abid
"""
import os
import simpleaudio as sa
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
from google.googleTTS import googleTTS


class marvinChat():

    def __init__(self):
        self.startProcess = True
        self.cur_path = os.path.dirname(os.path.abspath(__file__))

        self.chatbot = ChatBot('MarvinEn', storage_adapter='chatterbot.storage.SQLStorageAdapter', database_uri='sqlite:///marvinen.sqlite3')
        self.trainer = ChatterBotCorpusTrainer(self.chatbot)
        self.trainer.train("chatterbot.corpus.english")

        self.chatbotAr = ChatBot('MarvinAr', storage_adapter='chatterbot.storage.SQLStorageAdapter', database_uri='sqlite:///marvinar.sqlite3')
        self.trainerAr = ChatterBotCorpusTrainer(self.chatbotAr)
        #self.trainerAr.train("chatterbot.corpus.arabic")
        self.trainerAr.train(self.cur_path + "/corpus/arabic/conversations.yml")

        self.gotts = googleTTS()
        self.data_dir = self.cur_path + "/google/data/"

    def justPlay(self, filename):
        wave_obj = sa.WaveObject.from_wave_file(filename)
        play_obj = wave_obj.play()
        play_obj.wait_done()

    def speechToTextGoogle(self, audio_base64, audio_type, lang):

        filename = self.gotts.save_file(audio_type, audio_base64)
        text = self.gotts.speech_to_text(filename, lang)
        return text

    def textToSpeechGoogle(self, message, lang):

        filename = self.gotts.text_to_speech(message, lang)
        if filename != "":
            self.justPlay(self.data_dir + filename)
        else:
            self.justPlay(self.cur_path + "/audios/wrong.wav")

    def replyToUserLocal(self, text, lang):
        if text == "":
            self.justPlay(self.cur_path + "/audios/wrong.wav")
        else:
            if lang == "ar":
                response = self.chatbotAr.get_response(text)
                #return response
                #print(response)
                self.textToSpeechGoogle(str(response), lang)
            else:
                response = self.chatbot.get_response(text)
                #return response
                #print(response)
                self.textToSpeechGoogle(str(response), lang)
