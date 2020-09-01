
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 31 11:47:50 2020

@author: Muhammad Abid

This program is the main program.
The basic functionality of the program is same as alexa or any other Voice controlled virtual assistant AI
The program activates on the word marvin and once it recognises your voice, you can ask anything from it which are programed.

The program can either be forced stoped or you have to say "marvin" then once it recognize your voice you have to say "can you stop now"
"""

import io
import os
import wave
import signal
import base64
import librosa
import pyaudio
import numpy as np

from speech import langmodel
from marvinChatter import marvinChat

"""
Global variable to terminate the program once you say can you stop now
"""
terminate = False

class Application():

	def __init__(self):
		#this varible is used to stop reading audio when some command is processing
		self.startProcess = True

		#This is the rate on which the recoding is done
		self.rate = 16000
		#This is used to read data from audio device, like how many time we read data in a second
		self.chunk = int(self.rate/20)

	"""
	This function is used to read data from stream based on the chunk size
	"""
	def readFromStream(self, stream):
		bytesData = stream.read(self.chunk)
		data = np.fromstring(bytesData, dtype=np.int16)
		return data, bytesData

	"""
	This function is used to write a wave file to filename location
	"""
	def writeWav(self, filename, data, sample_size):
		wf = wave.open(filename, 'wb')
		wf.setnchannels(1)
		wf.setsampwidth(sample_size)
		wf.setframerate(self.rate)
		wf.writeframes(data)
		wf.close()

	"""
	This function is used to get the base64 value of the wave file which we need to send to the server
	"""
	def getBase64(self, file_path):
	    with io.open(file_path, "rb") as f:
	        content = f.read()

	    base64_data = base64.b64encode(content)
	    return base64_data.decode("utf-8")

	"""
	This is the program which will run modules based on what you said.
	E.g
		You say "marvin"
		If it recognise what you said it will play a sound
		After the sound you can order marvin to perform tasks.
		example command "can you start camera" it will start the camera module
	"""
	def run(self):

		# Importing the global varibales
		global terminate

		"""
		This is the speech model to recognise the word marvin.
		"""
		speechModel = langmodel.speechModel()

		"""
		This is the chat module, there are specific words and answers to it which are listed in the marvinChat module
		"""
		mChat = marvinChat()

		"""
		These functions are used to read the audio from the microphone.
		"""
		p = pyaudio.PyAudio()
		stream = p.open(format=pyaudio.paInt16, channels=1, rate=self.rate, input=True, frames_per_buffer=self.chunk)
		sample_size = p.get_sample_size(pyaudio.paInt16)

		
		"""
		These are the required varible definition.
		"""

		stopNow = False
		recordNow = False
		highPitch = False
		chunkAdded = False
		lang = "en"

		datasec = []
		tobeCheck = []
		tobeSent = []
		data_chunk = []
		bytes_chunk = []


		"""
		Playing a sound to let user know that marvin is ready.
		"""

		mChat.justPlay("audios/ready.wav")

		while stopNow == False:
			
			data, bytesData = self.readFromStream(stream)

			"""
			This is to control that if person is talking or now.
			The value 2500 depends on the volume of the device
			The current setting of the PC where program runs
			Ubuntu 20.04, volume is on 45%
			If the volume of the audio device goes up then max() value will be different.
			This function needs to be refined like noise removal etc
			"""
			if max(data) > 2500:
				highPitch = True

			"""
			We process data only when we get a high pitch sound
			We also check if there is command running at a time
			"""
			if highPitch and self.startProcess:
				"""
				We are making a chunks of data here
				To recognise word marvin we create one second chunk of data
				To recognise command we make three seconds chunk of data
				Some data is missing so we save last chunk of data and add it to initial.
				"""
				if chunkAdded == False:
					#print(bytes_chunk)
					if len(bytes_chunk) > 0:
						datasec.extend(data_chunk)
						tobeCheck.append(bytes_chunk)
						tobeSent.append(bytes_chunk)
					chunkAdded = True
				"""
				This varible is used for the local marvin model
				"""
				tobeCheck.append(bytesData)
				if recordNow == False:
					datasec.extend(data)
					#print(len(datasec))
					if len(datasec) == 16000:
						"""
						If we have one second data we will now try to predict if user said marvin or not.
						"""
						self.startProcess = False
						chunkAdded = False
						highPitch = False
						#print(tobeCheck)
						self.writeWav("audios/check.wav", b''.join(tobeCheck), sample_size)
						sample, sample_rate = librosa.load("audios/check.wav", sr = 16000)
						predictData = librosa.resample(sample, 16000, 8000)
						#print(len(predictData))
						#index, prob = predict(sample)
						label, maxProb, prob = speechModel.predictWord(sample)
						print("prediction ----")
						print("label:" + str(label) + " probability: " + str(maxProb))
						
						""" If you want to close the program on stop label predicted by our model, you can do so by enabling below code"""
						# if label == 'stop' and maxProb > 0.5:
						# 	stopNow = True
						# 	terminate = True

						# If the word marvin is recognised and probablity of being word marvin.
						if label == 'marvin' and maxProb > 0.18:
							print("recording now....")
							recordNow = True
							mChat.justPlay("audios/bell.wav")
						
						#Resetting the varible to make it run next time
						tobeCheck = []
						tobeSent = []
						datasec = []
						self.startProcess = True
				else:

					"""
					This varible is used for the three second command which is translated by Google
					"""
					tobeSent.append(bytesData)

					# check if we collect three seconds of data
					if len(tobeCheck) == 60:
						"""
						We send three seconds data to google server for translations
						We perform tasks based on the text we get from google
						"""
						self.startProcess = False
						print("answering now....")
						chunkAdded = False
						highPitch = False

						#send data to server to process
						self.writeWav("audios/send.wav", b''.join(tobeSent), sample_size)
						recordNow = False
						tobeCheck = []
						tobeSent = []
						datasec = []

						""" calling the google api to translate speech to text """

						text = mChat.speechToTextGoogle(self.getBase64("audios/send.wav"), "wav", lang)
						
						# Making all text lowercase so that it will be easier when comparing and doing acording to commands
						text = text.lower()

						print("speech to text")
						print(text)

						"""
						If dance module or pose module is started we are not entertaining any commands other then shutting down pose module or dance module
						"""

						if "language" in text or "اللغه" in text:
							"""
							We are changing language on the command
							commands:
							change language to english
							change language to arabic
							"""
							if "english" in text or "الانجليزيه" in text:
								lang = "en"
								text = "Language is changed to english now"
								text_ar = "تم تغيير اللغة إلى الإنجليزية الآن"
								text = text_ar if lang == "ar" else text

								mChat.textToSpeechGoogle(text, lang)
							elif "arabic" in text or "العربية" in text:
								lang = "ar"
								text = "Language is changed to arabic now"
								text_ar = "تم تغيير اللغة إلى العربية الآن"
								text = text_ar if lang == "ar" else text

								mChat.textToSpeechGoogle(text, lang)
						elif ("stop" in text and "now" in text) or "توقف" in text:
							stopNow = True
							terminate = True
						else:
							"""
							If no command is found then we will run the chat module, and ask it to answer the question
							for example: how are you?
							it will reply according to chat module database marvinChat.
							"""
							print("talking to marvin")
							mChat.replyToUserLocal(text, lang)
						
						self.startProcess = True

			"""
			save the last decoding data and bytes data which we attach to the start of the voice
			"""
			data_chunk = data
			bytes_chunk = bytesData

		"""
		Shutdown the audio stream.
		"""
		stream.stop_stream()
		stream.close()
		p.terminate()

"""
This is the main program which runs all the modules
All the processes are running as sub processes so that if main process is forced to shut down sub processes will shut down too.
"""

if __name__=="__main__":

	startMarvin = True
	# run the main program until terminate is false
	while terminate == False:
		try:
			if startMarvin:
				startMarvin = False
				
				# starting the python program to send commands to unity program
				app = Application()
				app.run()
		except Exception as e:
			startMarvin = True
			print(e)

