# -*- coding: utf-8 -*-
"""
Created on Mon Aug 31 11:47:50 2020

@author: Muhammad Abid
"""
import os
import numpy as np
from .model import speech_model, prepare_model_settings


class speechModel():
	def __init__(self):
		self.dir_path = os.path.dirname(os.path.abspath(__file__))
		self.output_representation = 'raw'
		self.sample_rate = 16000
		self.classes = 'sheila nine stop bed four six down bird marvin cat off right seven eight up three happy go zero on wow dog yes five one tree house two left no kidmak' 
		self.classes = ["_silence_", "_unknown_"] + self.classes.split(' ')

		self.model_settings = prepare_model_settings(label_count=len(self.classes), sample_rate=self.sample_rate, clip_duration_ms=1000, window_size_ms=30.0, window_stride_ms=10.0,
													dct_coefficient_count=80, num_log_mel_features=60, output_representation=self.output_representation)

		self.speechModel = speech_model( 'conv_1d_time_sliced_with_attention',
			      self.model_settings['fingerprint_size'] if self.output_representation != 'raw' else self.model_settings['desired_samples'],  # noqa
			      num_classes=self.model_settings['label_count'], **self.model_settings)
		
		self.speechModel.load_weights(self.dir_path +"/speech_model.hdf5")


	def predictWord(self, speech):

		prob = self.speechModel.predict(speech.reshape(1,16000))
		maxProb = max(prob[0])
		probClass = self.classes[np.argmax(prob[0])]
		return probClass, maxProb, prob[0]
