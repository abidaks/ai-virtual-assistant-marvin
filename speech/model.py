import keras
from tensorflow.compat.v1.keras import backend as K
from keras.layers import *
from keras.layers.noise import AlphaDropout
from keras.regularizers import l2
from keras.activations import softmax
from keras.models import Model
from keras.layers import DepthwiseConv2D
import tensorflow.compat.v1 as tf

from .utils import smooth_categorical_crossentropy

@tf.function
def preprocess(x):
  x = (x + 0.8) / 7.0
  x = tf.clip_by_value(x, -5, 5)
  return x

def preprocess_raw(x):
  # x = K.pow(10.0, x) - 1.0
  return x

@tf.function
def relu6(x):
  return tf.nn.relu6(x)

@tf.function
def _depthwise_conv_block(
        x, num_filter, k, padding='same', use_bias=False,
        dilation_rate=1, intermediate_activation=False,
        strides=1, l2_reg=1e-5):
  x = tf.expand_dims(x, 1)
  x = tf.keras.layers.DepthwiseConv2D(
      (1, k), padding=padding, use_bias=use_bias,
      dilation_rate=dilation_rate, strides=strides,
      kernel_regularizer=tf.keras.regularizers.l2(l2_reg))(x)
  x = tf.squeeze(x, 1)
  if intermediate_activation:
    x = tf.keras.layers.BatchNormalization()(x)
    x = Activation(relu6)(x)
  x = tf.keras.layers.Conv1D(num_filter, 1, use_bias=use_bias,
             kernel_regularizer=tf.keras.regularizers.l2(l2_reg))(x)
  x = tf.keras.layers.BatchNormalization()(x)
  x = Activation(relu6)(x)
  return x


import tensorflow as tf

def time_slice_stack(x, step):
    # Get the shape of x
    shape = tf.shape(x)
    # Create a sequence of indices for the slices
    idx = tf.range(start=0, limit=shape[1], delta=step)
    # Use tf.gather to get the slices from x
    x_slices = tf.gather(x, idx, axis=1)
    # Add a new dimension to the slices
    x_slices = tf.expand_dims(x_slices, axis=-1)
    # Concatenate the slices along the last dimension
    x_slices = tf.concat(x_slices, axis=-1)
    return x_slices

def overlapping_time_slice_stack(x, ksize, stride, padding='SAME'):
    # Use tf.signal.frame to get the overlapping slices
    x_slices = tf.signal.frame(x, ksize, stride, padding=padding)
    return x_slices

def snn_model(input_size=16000, num_classes=11):
    input_layer = tf.keras.layers.Input(shape=[input_size])
    activation = 'selu'
    kernel_initializer = 'lecun_normal'
    x = input_layer
    x = Preprocess(x)
    for num_hidden, dropout_ratio in [
            (512, 0.1), (256, 0.1), (128, 0.1), (64, 0.05)]:
        x = tf.keras.layers.Dense(num_hidden, activation=activation,
                                kernel_initializer=kernel_initializer)(x)
        x = tf.keras.layers.AlphaDropout(dropout_ratio)(x)

    x = tf.keras.layers.Dense(num_classes, activation='softmax',
                            kernel_initializer=kernel_initializer)(x)

    model = tf.keras.Model(input_layer, x, name='speech_model')
    model.compile(
        optimizer=tf.keras.optimizers.SGD(lr=0.01, momentum=0.9),
        loss=tf.keras.losses.categorical_crossentropy,
        metrics=[tf.keras.metrics.categorical_accuracy])
    return model

def simple_model(input_size=16000, num_classes=11):
    input_layer = tf.keras.layers.Input(shape=[input_size])
    x = input_layer
    x = Preprocess(x)
    x = tf.keras.layers.Dense(num_classes, activation='softmax')(x)

    model = tf.keras.Model(input_layer, x, name='speech_model')
    model.compile(
        optimizer=tf.keras.optimizers.SGD(lr=0.01, momentum=0.9),
        loss=tf.keras.losses.categorical_crossentropy,

import tensorflow as tf

def conv_1d_simple_model(input_size=16000, num_classes=11):
    input_layer = tf.keras.layers.Input(shape=[input_size])
    x = input_layer
    x = PreprocessRaw(x)
    x = tf.keras.layers.Reshape([-1, 1])(x)

    def _reduce_conv(x, num_filters, k, strides=2, padding='valid'):
        x = _depthwise_conv_block(
            x, num_filters, k, padding=padding, use_bias=False,
            strides=strides)
        return x

    def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
        x = _depthwise_conv_block(
            x, num_filters, k, padding=padding, dilation_rate=dilation_rate,
            use_bias=False)
        return x

    x = _reduce_conv(x, 32, 31, strides=16)  # 8000
    x = _context_conv(x, 32, 3)
    for num_hidden in [64, 96, 128, 160, 192, 224]:
        x = _reduce_conv(x, num_hidden, 3)  # 4000
        x = _context_conv(x, num_hidden, 3)

    x = tf.keras.layers.Bidirectional(tf.keras.layers.GRU(128, dropout=0.2, recurrent_dropout=0.2))(x)
    x = tf.keras.layers.Dense(num_classes, activation='softmax')(x)

    model = tf.keras.Model(input_layer, x, name='conv_1d_time_stacked')
    model.compile(
        optimizer=tf.keras.optimizers.Adam(),
        loss=tf.keras.losses.categorical_crossentropy,
        metrics=[tf.keras.metrics.categorical_accuracy])
    return model

def conv_1d_inception_model(input_size=16000, num_classes=11):
    input_layer = tf.keras.layers.Input(shape=[input_size])
    x = input_layer
    x = PreprocessRaw(x)
    x = tf.keras.layers.Reshape([-1, 1])(x)

    def _reduce_conv(x, num_filters, k, strides=2, padding='same'):
        x = tf.keras.layers.Conv1D(num_filters, k, padding=padding, strides=strides,
                       kernel_regularizer=tf.keras.regularizers.l2(0.00001), use_bias=False)(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation(tf.nn.relu6)(x)
        return x


  def _inception_block(x, base_num, block_id):
    branch1x1 = _context_conv(x, int(2 * base_num), 1)

    branch5x5 = _context_conv(x, int(1.5 * base_num), 1)
    branch5x5 = _context_conv(branch5x5, int(2 * base_num), 5)

    branch3x3dbl = _context_conv(x, int(2 * base_num), 1)
    branch3x3dbl = _context_conv(branch3x3dbl, int(3 * base_num), 3)
    branch3x3dbl = _context_conv(branch3x3dbl, int(3 * base_num), 3)

    branch_pool = AveragePooling1D(3, strides=1, padding='same')(x)
    branch_pool = _context_conv(branch_pool, base_num, 1)
    x = Concatenate(name='mixed%d' % block_id)(
        [branch1x1, branch5x5, branch3x3dbl, branch_pool])
    return x

  def _reduce_inception_block(x, base_num, strides, block_id):
    branch3x3 = _reduce_conv(x, int(6 * base_num), 3, strides=strides,
                             padding='valid')

    branch3x3dbl = _context_conv(x, base_num, 1)
    branch3x3dbl = _context_conv(branch3x3dbl, int(1.5 * base_num), 3)
    branch3x3dbl = _reduce_conv(branch3x3dbl, int(1.5 * base_num), 3,
                                strides=strides, padding='valid')

    branch_pool = MaxPool1D(3, strides=strides)(x)
    x = Concatenate(name='mixed%d' % block_id)(
        [branch3x3, branch3x3dbl, branch_pool])
    return x

  x = _stem(x)
  x = _inception_block(x, base_num=32, block_id=1)
  x = _inception_block(x, base_num=16, block_id=2)
  x = _reduce_inception_block(x, base_num=32, strides=2, block_id=3)
  x = _inception_block(x, base_num=32, block_id=4)
  x = _inception_block(x, base_num=32, block_id=5)
  x = _reduce_inception_block(x, base_num=64, strides=2, block_id=6)
  x = _inception_block(x, base_num=64, block_id=7)
  x = _inception_block(x, base_num=64, block_id=8)
  x = _reduce_inception_block(x, base_num=96, strides=2, block_id=9)
  x = _inception_block(x, base_num=96, block_id=10)
  x = _inception_block(x, base_num=96, block_id=11)

  x = Dropout(0.15)(x)
  x = Conv1D(num_classes, 14, activation='softmax', padding='valid')(x)
  x = Reshape([-1])(x)

  model = Model(input_layer, x, name='conv_1d_time_stacked')
  model.compile(
      optimizer=keras.optimizers.Adam(),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_time_stacked_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  input_layer = Input(shape=[input_size])
  x = input_layer
  x = Reshape([800, 20])(x)
  x = PreprocessRaw(x)

  def _reduce_conv(x, num_filters, k, strides=2, padding='valid'):
    x = Conv1D(num_filters, k, padding=padding, use_bias=False,
               kernel_regularizer=l2(0.00001))(x)
    x = BatchNormalization()(x)
    x = Activation(relu6)(x)
    x = MaxPool1D(pool_size=3, strides=strides, padding=padding)(x)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
    x = Conv1D(num_filters, k, padding=padding, dilation_rate=dilation_rate,
               kernel_regularizer=l2(0.00001), use_bias=False)(x)
    x = BatchNormalization()(x)
    x = Activation(relu6)(x)
    return x

  x = _context_conv(x, 32, 1)
  x = _reduce_conv(x, 48, 3)
  x = _context_conv(x, 48, 3)
  x = _reduce_conv(x, 96, 3)
  x = _context_conv(x, 96, 3)
  x = _reduce_conv(x, 128, 3)
  x = _context_conv(x, 128, 3)
  x = _reduce_conv(x, 160, 3)
  x = _context_conv(x, 160, 3)
  x = _reduce_conv(x, 192, 3)
  x = _context_conv(x, 192, 3)
  x = _reduce_conv(x, 256, 3)
  x = _context_conv(x, 256, 3)

  x = Dropout(0.3)(x)
  x = Conv1D(num_classes, 5, activation='softmax')(x)
  x = Reshape([-1])(x)

  model = Model(input_layer, x, name='conv_1d_time_stacked')
  model.compile(
      optimizer=keras.optimizers.Adam(lr=3e-4),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_inception_d1_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  input_layer = Input(shape=[input_size])
  x = input_layer
  x = Reshape([800, 20])(x)
  x = PreprocessRaw(x)

  def _reduce_conv(x, num_filters, k, strides=2, padding='same'):
    x = Conv1D(num_filters, k, padding=padding, use_bias=False,
               kernel_regularizer=l2(0.00001))(x)
    x = BatchNormalization()(x)
    x = Activation(relu6)(x)
    x = MaxPool1D(pool_size=3, strides=strides, padding=padding)(x)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='same'):
    x = Conv1D(num_filters, k, padding=padding, dilation_rate=dilation_rate,
               kernel_regularizer=l2(0.00001), use_bias=False)(x)
    x = BatchNormalization()(x)
    x = Activation(relu6)(x)
    return x

  def _inception_block(x, base_num, block_id, dilation_rate=1):
    branch1x1 = _context_conv(x, int(2 * base_num), 1)

    branch5x5 = _context_conv(x, int(1.5 * base_num), 1)
    branch5x5 = _context_conv(branch5x5, int(2 * base_num), 3, dilation_rate=2)

    branch3x3dbl = _context_conv(x, int(2 * base_num), 1)
    branch3x3dbl = _context_conv(
        branch3x3dbl, int(3 * base_num), 3, dilation_rate=dilation_rate)
    branch3x3dbl = _context_conv(
        branch3x3dbl, int(3 * base_num), 3, dilation_rate=dilation_rate)

    branch_pool = AveragePooling1D(pool_size=3, strides=1, padding='same')(x)
    branch_pool = _context_conv(branch_pool, base_num, 1)
    x = Concatenate(name='mixed%d' % block_id)(
        [branch1x1, branch5x5, branch3x3dbl, branch_pool])
    return x

  def _reduce_inception_block(x, base_num, strides, block_id):
    branch3x3 = _reduce_conv(x, int(6 * base_num), 3, strides=strides)

    branch3x3dbl = _context_conv(x, base_num, 1)
    branch3x3dbl = _context_conv(branch3x3dbl, int(1.5 * base_num), 3)
    branch3x3dbl = _reduce_conv(branch3x3dbl, int(1.5 * base_num), 3,
                                strides=strides, padding='same')

    branch_pool = MaxPool1D(3, strides=strides, padding='same')(x)
    x = Concatenate(name='mixed%d' % block_id)(
        [branch3x3, branch3x3dbl, branch_pool])
    return x

  # stem: output @ ~100
  x = _context_conv(x, 32, 1)
  x = _reduce_conv(x, 64, 3, padding='valid')
  x = _context_conv(x, 64, 3, padding='valid')
  x = _reduce_conv(x, 128, 3, padding='valid')
  x = _context_conv(x, 128, 3, padding='valid')
  x = _reduce_conv(x, 256, 3, padding='valid')
  x = _context_conv(x, 256, 3, padding='valid')
  # inception block 1: output @ ~50
  x = _inception_block(x, base_num=32, block_id=1, dilation_rate=2)
  x = _inception_block(x, base_num=32, block_id=2, dilation_rate=2)
  x = _reduce_inception_block(x, base_num=32, strides=2, block_id=3)
  # inception block 2: @ ~24
  x = _inception_block(x, base_num=32, block_id=4, dilation_rate=2)
  x = _inception_block(x, base_num=32, block_id=5)
  x = _reduce_inception_block(x, base_num=32, strides=2, block_id=6)
  # inception block 3: @ ~12
  x = _inception_block(x, base_num=32, block_id=7)
  x = _inception_block(x, base_num=32, block_id=8)
  x = _reduce_inception_block(x, base_num=32, strides=2, block_id=9)
  # inception block 4: @ ~6
  x = _inception_block(x, base_num=32, block_id=10)
  x = _inception_block(x, base_num=32, block_id=11)
  x = _reduce_inception_block(x, base_num=32, strides=2, block_id=12)

  x = Dropout(0.2)(x)
  x = Conv1D(num_classes, 6, activation='softmax')(x)
  x = Reshape([-1])(x)

  model = Model(input_layer, x, name='inception_d1')
  model.compile(
      optimizer=keras.optimizers.Adam(lr=0.001),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_heavy_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  input_layer = Input(shape=[input_size])
  x = input_layer
  x = Reshape([1600, 10])(x)
  x = PreprocessRaw(x)

  def _reduce_conv(x, num_filters, k, strides=2, padding='valid'):
    x = Conv1D(num_filters, k, padding=padding, use_bias=False,
               kernel_regularizer=l2(0.00001))(x)
    x = BatchNormalization()(x)
    x = Activation(relu6)(x)
    x = MaxPool1D(pool_size=3, strides=strides, padding=padding)(x)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
    x = Conv1D(num_filters, k, padding=padding, dilation_rate=dilation_rate,
               kernel_regularizer=l2(0.00001), use_bias=False)(x)
    x = BatchNormalization()(x)
    x = Activation(relu6)(x)
    return x

  x = _context_conv(x, 32, 1)
  x = _reduce_conv(x, 48, 3)
  x = _context_conv(x, 48, 3)
  x = _reduce_conv(x, 96, 3)
  x = _context_conv(x, 96, 3)
  x = _reduce_conv(x, 128, 3)
  x = _context_conv(x, 128, 3)
  x = _reduce_conv(x, 160, 3)
  x = _context_conv(x, 160, 3)
  x = _reduce_conv(x, 192, 3)
  x = _context_conv(x, 192, 3)
  x = _reduce_conv(x, 256, 3)
  x = _context_conv(x, 256, 3)
  x = _reduce_conv(x, 320, 3)
  x = _context_conv(x, 320, 3)

  x = Dropout(0.3)(x)
  x = Conv1D(128, 5, use_bias=False)(x)
  x = BatchNormalization()(x)
  x = Activation(relu6)(x)
  x = Dropout(0.1)(x)
  x = Conv1D(num_classes, 1, activation='softmax', use_bias=False)(x)
  x = Reshape([-1])(x)

  model = Model(input_layer, x, name='conv_1d_time_stacked')
  model.compile(
      optimizer=keras.optimizers.Adam(lr=3e-4),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_gru_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  def _reduce_conv(x, num_filters, k, strides=2, padding='same'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, use_bias=False,
        strides=strides)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, dilation_rate=dilation_rate,
        use_bias=False)
    return x

  input_layer = Input(shape=[input_size])
  x = input_layer
  x = PreprocessRaw(x)
  x = Reshape([-1, 1])(x)
  x = _reduce_conv(x, 128, 63, strides=16)  # 1000
  x = _reduce_conv(x, 256, 31, strides=4)  # 250
  x = _reduce_conv(x, 384, 15, strides=4)  # 64
  x = _reduce_conv(x, 448, 7, strides=4)  # 16
  x = _reduce_conv(x, 512, 5, strides=2)  # 8
  x = _context_conv(x, 512, 8)  # 8
  x = Flatten()(x)
  x = Dropout(0.3)(x)
  x = Activation(relu6)(Dense(256)(x))
  x = Dropout(0.3)(x)
  x = Dense(num_classes, activation='softmax')(x)

  model = Model(input_layer, x, name='conv_1d_bigru')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=1e-3),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_2d_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = True. This is the keras version of:
  https://github.com/tensorflow/tensorflow/blob/master/tensorflow/examples/speech_commands/models.py#L165-L270  # noqa
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  # TODO(see--): Allow variable sized frequency_size & time_size
  frequency_size = 40
  time_size = 98
  input_layer = Input(shape=[input_size])
  x = input_layer
  x = Reshape([time_size, frequency_size, 1])(x)
  x = Preprocess(x)
  x = Conv2D(64, kernel_size=(20, 8), padding='same', activation='relu')(x)
  x = MaxPool2D()(x)
  x = Conv2D(128, kernel_size=(10, 4), padding='same', activation='relu')(x)
  x = MaxPool2D()(x)
  x = Flatten()(x)
  x = Dense(num_classes, activation='softmax')(x)

  model = Model(input_layer, x, name='speech_model')
  model.compile(
      optimizer=keras.optimizers.SGD(lr=0.001, momentum=0.9),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_2d_mobile_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = True. This is the keras version of:
  https://github.com/tensorflow/tensorflow/blob/master/tensorflow/examples/speech_commands/models.py#L165-L270  # noqa
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  # TODO(see--): Allow variable sized frequency_size & time_size
  time_size = 98
  frequency_size = 40
  input_layer = Input(shape=[input_size])
  x = input_layer
  x = Reshape([time_size, frequency_size, 1])(x)
  x = Preprocess(x)

  def _conv_bn_relu6(x, num_filter, kernel=(3, 3), strides=(1, 1)):
    x = Conv2D(num_filter, kernel, padding='same',
               strides=strides)(x)
    x = BatchNormalization()(x)
    x = Activation(relu6)(x)
    return x

  x = _conv_bn_relu6(x, 32, strides=2)  # (49, 20)
  x = _conv_bn_relu6(x, 32)  # (49, 20)
  x = Dropout(0.05)(x)
  x = _conv_bn_relu6(x, 64, strides=2)  # (25, 10)
  x = _conv_bn_relu6(x, 64)  # (25, 10)
  x = Dropout(0.05)(x)
  x = _conv_bn_relu6(x, 128, strides=2)  # (13, 5)
  x = _conv_bn_relu6(x, 128)  # (13, 5)
  x = Dropout(0.05)(x)
  x = _conv_bn_relu6(x, 256, strides=2)  # (7, 3)
  x = _conv_bn_relu6(x, 256)  # (7, 3)
  x = Dropout(0.05)(x)

  x = GlobalAveragePooling2D()(x)
  x = Dropout(0.1)(x)
  x = Dense(num_classes, activation='softmax')(x)

  model = Model(input_layer, x, name='conv_2d_mobile')
  model.compile(
      optimizer=keras.optimizers.SGD(lr=0.001, momentum=0.95),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_2d_fast_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = True. This is the keras version of:
  https://github.com/tensorflow/tensorflow/blob/master/tensorflow/examples/speech_commands/models.py#L165-L270  # noqa
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  # TODO(see--): Allow variable sized frequency_size & time_size
  time_size = 98
  frequency_size = 40
  input_layer = Input(shape=[input_size])
  x = input_layer
  x = Reshape([time_size, frequency_size, 1])(x)
  x = Preprocess(x)

  def _conv_bn(x, num_filter, kernel_size, dilation_rate):
    x = Conv2D(num_filter, kernel_size=kernel_size, padding='same',
               dilation_rate=dilation_rate)(x)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)
    return x

  def _conv_bn_pool(x, num_filter, kernel_size, dilation_rate):
    x = _conv_bn(x, num_filter, kernel_size, dilation_rate)
    x = MaxPool2D()(x)
    return x

  x = _conv_bn_pool(x, 16, (11, 5), (2, 1))  # (49, 20)
  x = _conv_bn_pool(x, 32, (5, 3), (2, 1))  # (25, 10)
  x = _conv_bn_pool(x, 64, (3, 3), (1, 1))  # (13, 5)
  x = _conv_bn_pool(x, 128, (3, 3), (1, 1))  # (7, 3)
  x = GlobalAveragePooling2D()(x)
  x = Dense(num_classes, activation='softmax')(x)

  model = Model(input_layer, x, name='conv_2d_fast')
  model.compile(
      optimizer=keras.optimizers.SGD(lr=0.001, momentum=0.9),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_fast_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  def _grouped_reduce_conv(x, num_filters, k, g, num_channels,
                           strides=2, padding='valid'):
    groups = []
    assert g >= 1
    assert num_channels % g == 0
    assert num_filters % g == 0
    group_size = int(num_channels / g)
    num_filters_per_group = int(num_filters / g)
    for i in range(g):
      group_start = i * group_size
      group_end = (i + 1) * group_size
      group = Lambda(lambda x: x[:, :, group_start: group_end])(x)
      group = Conv1D(
          num_filters_per_group, k, padding=padding, use_bias=False,
          strides=strides)(group)
      group = BatchNormalization()(group)
      group = Activation(relu6)(group)
      groups.append(group)
    if g == 1:
      return groups[0]
    return Concatenate()(groups)

  def _grouped_context_conv(x, num_filters, k, g, num_channels,
                            dilation_rate=1, padding='valid'):
    groups = []
    assert g >= 1
    assert num_channels % g == 0
    assert num_filters % g == 0
    group_size = int(num_channels / g)
    num_filters_per_group = int(num_filters / g)
    for i in range(g):
      group_start = i * group_size
      group_end = (i + 1) * group_size
      group = Lambda(lambda x: x[:, :, group_start: group_end])(x)
      group = Conv1D(
          num_filters_per_group, k, use_bias=False,
          padding=padding, dilation_rate=dilation_rate)(group)
      group = BatchNormalization()(group)
      group = Activation(relu6)(group)
      groups.append(group)
    if g == 1:
      return groups[0]
    return Concatenate()(groups)

  input_layer = Input(shape=[input_size])
  x = input_layer
  x = PreprocessRaw(x)
  x = Reshape([-1, 1])(x)
  x = Conv1D(252, 479, strides=160, kernel_regularizer=l2(0.0001),
             use_bias=False)(x)  # 98
  x = _grouped_reduce_conv(x, 300, 15, 6, 252)  # 76
  x = _grouped_reduce_conv(x, 360, 7, 5, 300)  # 76

  x = Flatten()(x)
  x = Dropout(0.3)(x)
  x = Dense(num_classes, activation='softmax')(x)

  model = Model(input_layer, x, name='conv_1d_learned_spec')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=3e-3),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_time_sliced_model(input_size=16000, num_classes=11, filter_mult=1):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  input_layer = Input(shape=[input_size])
  x = input_layer
  x = PreprocessRaw(x)

  def _reduce_conv(x, num_filters, k, strides=2, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, use_bias=False, strides=strides)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, dilation_rate=dilation_rate,
        use_bias=False)
    return x

  def _reduce_block(x, num_filters, k):
    x = _reduce_conv(x, num_filters, k, padding='same')
    x = _context_conv(x, num_filters, k, padding='valid')
    return x

  x = Lambda(lambda x: overlapping_time_slice_stack(x, 40, 20))(x)
  # default conv
  x = Conv1D(32 * filter_mult, 3, strides=2, use_bias=False,
             kernel_regularizer=l2(1e-5))(x)
  x = BatchNormalization()(x)
  x = Activation(relu6)(x)
  # depthwise conv
  x = _context_conv(x, 64 * filter_mult, 3)
  x = _reduce_block(x, 128 * filter_mult, 3)
  x = _reduce_block(x, 192 * filter_mult, 3)
  x = _reduce_block(x, 256 * filter_mult, 3)
  x = _reduce_block(x, 320 * filter_mult, 3)
  x = _reduce_block(x, 384 * filter_mult, 3)
  x = _reduce_block(x, 512 * filter_mult, 3)
  x = GlobalAveragePooling1D()(x)
  x = Dropout(0.4)(x)
  x = Dense(256 * filter_mult, use_bias=False)(x)
  x = Activation(relu6)(x)
  x = Dropout(0.3)(x)
  x = Dense(num_classes, activation='softmax', use_bias=False,
            kernel_regularizer=l2(1e-5))(x)

  model = Model(input_layer, x, name='conv_1d_time_sliced')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=1e-3),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_time_sliced_with_attention_model(
        input_size=16000, num_classes=11, filter_mult=1):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  input_layer = Input(shape=[input_size])
  x = input_layer
  x = PreprocessRaw(x)

  def _reduce_conv(x, num_filters, k, strides=2, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, use_bias=False, strides=strides)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, dilation_rate=dilation_rate,
        use_bias=False)
    return x

  def _reduce_block(x, num_filters, k):
    x = _reduce_conv(x, num_filters, k, padding='same')
    x = _context_conv(x, num_filters, k, padding='valid')
    return x

  x = Lambda(lambda x: overlapping_time_slice_stack(x, 40, 20))(x)
  # default conv
  x = Conv1D(128 * filter_mult, 3, strides=2, use_bias=False,
             kernel_regularizer=l2(1e-5))(x)
  x = BatchNormalization()(x)
  x = Activation(relu6)(x)
  # depthwise conv
  x = _context_conv(x, 128 * filter_mult, 3)
  x = _reduce_block(x, 192 * filter_mult, 3)
  x = _reduce_block(x, 256 * filter_mult, 3)
  x = _reduce_block(x, 320 * filter_mult, 3)
  x = _reduce_block(x, 384 * filter_mult, 3)
  x = _reduce_block(x, 512 * filter_mult, 3)

  attention = Dropout(0.4)(Flatten()(x))
  attention = Dense(9, activation='softmax',
                    kernel_regularizer=l2(1e-5))(attention)
  attention = Lambda(lambda x: K.expand_dims(x, axis=-1))(attention)

  attention = Multiply()([x, attention])
  x_max = GlobalMaxPool1D()(attention)
  x_avg = GlobalAveragePooling1D()(x)
  x = Concatenate()([x_max, x_avg])
  x = Dropout(0.4)(x)
  x = Dense(num_classes, activation='softmax', use_bias=False,
            kernel_regularizer=l2(1e-5))(x)

  model = Model(input_layer, x, name='conv_1d_time_sliced_with_attention')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=1e-3),
      loss=lambda y_true, y_pred: smooth_categorical_crossentropy(
          y_true, y_pred, label_smoothing=0.1),
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_residual_model(input_size=16000, num_classes=11, filter_mult=1):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  def _reduce_conv(x, num_filters, k, strides=2, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, use_bias=False, strides=strides)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, dilation_rate=dilation_rate,
        use_bias=False)
    return x

  def _reduce_block(x, num_filters, k):
    x = _reduce_conv(x, num_filters, k, padding='same')
    x = _context_conv(x, num_filters, k, padding='valid')
    return x

  def _residual_block(x, num_filters, k, strides=1, padding='same'):
    if strides != 1:
      residual = Conv1D(
          num_filters, 1, strides=strides, padding='same', use_bias=False)(x)
      residual = BatchNormalization()(residual)
    else:
      residual = x
    x = _depthwise_conv_block(
        x, num_filters, k, padding='same', use_bias=False)
    x = _depthwise_conv_block(
        x, num_filters, k, padding='same', use_bias=False)
    x = MaxPool1D(pool_size=3, strides=strides, padding='same')(x)
    return Add()([x, residual])

  input_layer = Input(shape=[input_size])
  x = input_layer
  x = PreprocessRaw(x)
  x = Lambda(lambda x: overlapping_time_slice_stack(x, 40, 20))(x)
  # default conv
  x = Conv1D(64 * filter_mult, 3, strides=2, use_bias=False,
             kernel_regularizer=l2(1e-5))(x)
  x = BatchNormalization()(x)
  x = Activation(relu6)(x)
  # depthwise conv
  x = _residual_block(x, 128 * filter_mult, 3, strides=2)  # 200
  x = _residual_block(x, 256 * filter_mult, 3, strides=2)  # 100
  for i in range(8):
    x = _residual_block(x, 256 * filter_mult, 3)
  x = _residual_block(x, 512 * filter_mult, 3, strides=2)
  x = _residual_block(x, 728 * filter_mult, 3, strides=2)
  x = _residual_block(x, 728 * filter_mult, 3, strides=2)
  x = _reduce_block(x, 1024 * filter_mult, 3)
  x = GlobalAveragePooling1D()(x)
  x = Dropout(0.5)(x)
  x = Dense(num_classes, activation='softmax',
            kernel_regularizer=l2(1e-5))(x)

  model = Model(input_layer, x, name='conv_1d_residual')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=1e-4),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def xception_with_attention_model(
        input_size=16000, num_classes=11, filter_mult=1):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  def _reduce_conv(x, num_filters, k, strides=2, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, use_bias=False, strides=strides)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, dilation_rate=dilation_rate,
        use_bias=False)
    return x

  def _reduce_block(x, num_filters, k):
    x = _reduce_conv(x, num_filters, k, padding='same')
    x = _context_conv(x, num_filters, k, padding='valid')
    return x

  def _residual_block(x, num_filters, k, strides=1, padding='same'):
    if strides != 1:
      residual = Conv1D(
          num_filters, 1, strides=strides, padding='same', use_bias=False)(x)
      residual = BatchNormalization()(residual)
    else:
      residual = x
    x = _depthwise_conv_block(
        x, num_filters, k, padding='same', use_bias=False)
    x = _depthwise_conv_block(
        x, num_filters, k, padding='same', use_bias=False)
    x = MaxPool1D(pool_size=3, strides=strides, padding='same')(x)
    return Add()([x, residual])

  input_layer = Input(shape=[input_size])
  x = input_layer
  x = PreprocessRaw(x)
  x = Lambda(lambda x: overlapping_time_slice_stack(x, 40, 20))(x)
  # default conv
  x = Conv1D(64 * filter_mult, 3, strides=2, use_bias=False,
             kernel_regularizer=l2(1e-5))(x)
  x = BatchNormalization()(x)
  x = Activation(relu6)(x)
  # depthwise conv
  x = _residual_block(x, 128 * filter_mult, 3, strides=2)  # 200
  x = _residual_block(x, 256 * filter_mult, 3, strides=2)  # 100
  for i in range(8):
    x = _residual_block(x, 256 * filter_mult, 3)
  x = _residual_block(x, 384 * filter_mult, 3, strides=2)

  # attention
  # https://github.com/philipperemy/keras-attention-mechanism/blob/master/attention_dense.py
  # attention before recurrent unit
  attention = _context_conv(x, 1, 5, padding='same')
  attention = Lambda(lambda x: softmax(x, axis=1))(attention)
  x = Multiply()([x, attention])
  x = Bidirectional(GRU(192, kernel_regularizer=l2(1e-5),
                        dropout=0.2, recurrent_dropout=0.2))(x)
  x = Dense(num_classes, activation='softmax',
            kernel_regularizer=l2(1e-5))(x)

  model = Model(input_layer, x, name='xception_with_attention')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=5e-4),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_time_sliced_group_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  input_layer = Input(shape=[input_size])
  x = input_layer
  x = PreprocessRaw(x)

  def _grouped_reduce_conv(x, num_filters, k, g, num_channels,
                           strides=2, padding='valid'):
    groups = []
    assert g >= 1
    assert num_channels % g == 0
    assert num_filters % g == 0
    group_size = int(num_channels / g)
    num_filters_per_group = int(num_filters / g)
    for i in range(g):
      group_start = i * group_size
      group_end = (i + 1) * group_size
      group = Lambda(lambda x: x[:, :, group_start: group_end])(x)
      group = _depthwise_conv_block(
          group, num_filters_per_group, k, padding=padding, use_bias=False,
          strides=strides)
      groups.append(group)
    if g == 1:
      return groups[0]
    return Concatenate()(groups)

  def _grouped_context_conv(x, num_filters, k, g, num_channels,
                            dilation_rate=1, padding='valid'):
    groups = []
    assert g >= 1
    assert num_channels % g == 0
    assert num_filters % g == 0
    group_size = int(num_channels / g)
    num_filters_per_group = int(num_filters / g)
    for i in range(g):
      group_start = i * group_size
      group_end = (i + 1) * group_size
      group = Lambda(lambda x: x[:, :, group_start: group_end])(x)
      group = _depthwise_conv_block(
          x, num_filters_per_group, k, use_bias=False,
          padding=padding, dilation_rate=dilation_rate)
      groups.append(group)
    if g == 1:
      return groups[0]
    return Concatenate()(groups)

  x500 = Reshape([500, 32])(x)
  x500 = _grouped_reduce_conv(x500, 64, 3, 4, 32)  # 250
  x500 = _grouped_context_conv(x500, 64, 3, 2, 64)
  x500 = _grouped_reduce_conv(x500, 128, 3, 4, 64)  # 125
  x500 = _grouped_context_conv(x500, 128, 3, 2, 128)
  x500 = _grouped_reduce_conv(x500, 160, 3, 4, 128)  # 125
  x500 = _grouped_context_conv(x500, 160, 3, 2, 160)
  x500 = _grouped_reduce_conv(x500, 192, 3, 4, 160)  # 64
  x500 = _grouped_context_conv(x500, 192, 3, 2, 192)
  x500 = _grouped_reduce_conv(x500, 224, 3, 4, 192)  # 32
  x500 = _grouped_context_conv(x500, 224, 3, 2, 224)
  x500 = _grouped_context_conv(x500, 224, 3, 2, 224)

  x400 = Reshape([400, 40])(x)
  x400 = _grouped_reduce_conv(x400, 64, 3, 4, 32)  # 250
  x400 = _grouped_context_conv(x400, 64, 3, 2, 64)
  x400 = _grouped_reduce_conv(x400, 128, 3, 4, 64)  # 125
  x400 = _grouped_context_conv(x400, 128, 3, 2, 128)
  x400 = _grouped_reduce_conv(x400, 160, 3, 4, 128)  # 125
  x400 = _grouped_context_conv(x400, 160, 3, 2, 160)
  x400 = _grouped_reduce_conv(x400, 192, 3, 4, 160)  # 64
  x400 = _grouped_context_conv(x400, 192, 3, 2, 192)
  x400 = _grouped_reduce_conv(x400, 224, 3, 4, 192)  # 32
  x400 = _grouped_context_conv(x400, 224, 3, 2, 224)
  x400 = ZeroPadding1D(padding=(1, 0))(x400)

  x = Concatenate()([x500, x400])
  x = Dropout(0.15)(x)
  x = Flatten()(Conv1D(128, 8)(x))
  x = Dropout(0.05)(x)
  x = Dense(num_classes, activation='softmax')(x)
  x = Reshape([-1])(x)

  model = Model(input_layer, x, name='conv_1d_time_sliced_group')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=1e-3),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_multi_time_sliced_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  input_layer = Input(shape=[input_size])
  x = input_layer
  x = PreprocessRaw(x)

  def _reduce_conv(x, num_filters, k, strides=2, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, use_bias=False)
    x = MaxPool1D(pool_size=3, strides=strides, padding='same')(x)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, dilation_rate=dilation_rate,
        use_bias=False)
    return x

  xs4 = Reshape([4000, 4])(x)  # 4000Hz
  xs4 = _reduce_conv(xs4, 16, 3)
  xs4 = _reduce_conv(xs4, 32, 3)
  xs4 = _reduce_conv(xs4, 48, 3)
  xs4 = _reduce_conv(xs4, 64, 3)
  xs4 = _reduce_conv(xs4, 96, 3)
  xs4 = _reduce_conv(xs4, 128, 3)
  xs4 = _reduce_conv(xs4, 160, 3)
  xs4 = _context_conv(xs4, 160, 3)
  xs4a = _context_conv(xs4, 64, 28)
  xs4 = _reduce_conv(xs4, 192, 3)
  xs4 = _context_conv(xs4, 192, 3)
  xs4b = _context_conv(xs4, 64, 11)

  xs5 = Reshape([3200, 5])(x)  # 3200Hz
  xs5 = _reduce_conv(xs5, 16, 3)
  xs5 = _reduce_conv(xs5, 32, 3)
  xs5 = _reduce_conv(xs5, 48, 3)
  xs5 = _reduce_conv(xs5, 64, 3)
  xs5 = _reduce_conv(xs5, 96, 3)
  xs5 = _reduce_conv(xs5, 128, 3)
  xs5 = _reduce_conv(xs5, 160, 3)
  xs5 = _context_conv(xs5, 160, 3)
  xs5a = _context_conv(xs5, 64, 22)
  xs5 = _reduce_conv(xs5, 192, 3)
  xs5 = _context_conv(xs5, 192, 3)
  xs5b = _context_conv(xs5, 64, 8)

  xs25 = Reshape([640, 25])(x)  # 640Hz
  xs25 = _reduce_conv(xs25, 32, 3)
  xs25 = _reduce_conv(xs25, 48, 3)
  xs25 = _reduce_conv(xs25, 64, 3)
  xs25 = _reduce_conv(xs25, 96, 3)
  xs25 = _reduce_conv(xs25, 128, 3)
  xs25 = _context_conv(xs25, 128, 3)
  xs25 = _context_conv(xs25, 64, 17)

  x = Concatenate(axis=-1)(
      [xs4a, xs4b, xs5a, xs5b, xs25])
  x = Dropout(0.1)(x)
  x = _context_conv(x, 128, 1)
  x = Dropout(0.1)(x)
  x = Conv1D(num_classes, 1, activation='softmax')(x)
  x = Reshape([-1])(x)

  model = Model(input_layer, x, name='conv_1d_multi_time_sliced')

  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=3e-3),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_learned_spec_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  def _grouped_reduce_conv(x, num_filters, k, g, num_channels,
                           strides=2, padding='valid'):
    groups = []
    assert g >= 1
    assert num_channels % g == 0
    assert num_filters % g == 0
    group_size = int(num_channels / g)
    num_filters_per_group = int(num_filters / g)
    for i in range(g):
      group_start = i * group_size
      group_end = (i + 1) * group_size
      group = Lambda(lambda x: x[:, :, group_start: group_end])(x)
      group = Conv1D(
          num_filters_per_group, k, padding=padding, use_bias=False,
          strides=strides)(group)
      group = BatchNormalization()(group)
      group = Activation(relu6)(group)
      groups.append(group)
    if g == 1:
      return groups[0]
    return Concatenate()(groups)

  def _grouped_context_conv(x, num_filters, k, g, num_channels,
                            dilation_rate=1, padding='valid'):
    groups = []
    assert g >= 1
    assert num_channels % g == 0
    assert num_filters % g == 0
    group_size = int(num_channels / g)
    num_filters_per_group = int(num_filters / g)
    for i in range(g):
      group_start = i * group_size
      group_end = (i + 1) * group_size
      group = Lambda(lambda x: x[:, :, group_start: group_end])(x)
      group = Conv1D(
          num_filters_per_group, k, use_bias=False,
          padding=padding, dilation_rate=dilation_rate)(group)
      group = BatchNormalization()(group)
      group = Activation(relu6)(group)
      groups.append(group)
    if g == 1:
      return groups[0]
    return Concatenate()(groups)

  input_layer = Input(shape=[input_size])
  x = input_layer
  x = PreprocessRaw(x)
  x = Reshape([-1, 1])(x)
  xw479 = Conv1D(40, 479, strides=160, kernel_regularizer=l2(0.0001),
                 use_bias=False, padding='same')(x)
  xw383 = Conv1D(40, 383, strides=160, kernel_regularizer=l2(0.0001),
                 use_bias=False, padding='same')(x)
  xw319 = Conv1D(40, 319, strides=160, kernel_regularizer=l2(0.0001),
                 use_bias=False, padding='same')(x)
  xw255 = Conv1D(40, 255, strides=160, kernel_regularizer=l2(0.0001),
                 use_bias=False, padding='same')(x)
  xw191 = Conv1D(40, 191, strides=160, kernel_regularizer=l2(0.0001),
                 use_bias=False, padding='same')(x)
  xw161 = Conv1D(40, 161, strides=160, kernel_regularizer=l2(0.0001),
                 use_bias=False, padding='same')(x)
  x = Concatenate()([xw479, xw383, xw319, xw255, xw191, xw161])
  x = _grouped_reduce_conv(x, 300, 3, 3, 240)  # 76
  x = _grouped_context_conv(x, 300, 3, 2, 360)
  x = _grouped_reduce_conv(x, 360, 3, 3, 300)  # 22
  x = _grouped_context_conv(x, 360, 3, 2, 360)
  x = _grouped_reduce_conv(x, 420, 3, 3, 240)  # 9
  x = _grouped_context_conv(x, 420, 3, 2, 420)
  x = _grouped_reduce_conv(x, 480, 3, 3, 420)  # 3
  x = _grouped_context_conv(x, 480, 3, 2, 480)
  x = Flatten()(x)
  x = Dropout(0.3)(x)
  x = Dense(num_classes, activation='softmax')(x)

  model = Model(input_layer, x, name='conv_1d_learned_spec')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=2e-3),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_spec_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  def _grouped_reduce_conv(x, num_filters, k, g, num_channels,
                           strides=2, padding='valid'):
    groups = []
    assert g >= 1
    assert num_channels % g == 0
    assert num_filters % g == 0
    group_size = int(num_channels / g)
    num_filters_per_group = int(num_filters / g)
    for i in range(g):
      group_start = i * group_size
      group_end = (i + 1) * group_size
      group = Lambda(lambda x: x[:, :, group_start: group_end])(x)
      group = Conv1D(
          num_filters_per_group, k, padding=padding, use_bias=False,
          strides=strides)(group)
      group = BatchNormalization()(group)
      group = Activation(relu6)(group)
      groups.append(group)
    if g == 1:
      return groups[0]
    return Concatenate()(groups)

  def _grouped_context_conv(x, num_filters, k, g, num_channels,
                            dilation_rate=1, padding='valid'):
    groups = []
    assert g >= 1
    assert num_channels % g == 0
    assert num_filters % g == 0
    group_size = int(num_channels / g)
    num_filters_per_group = int(num_filters / g)
    for i in range(g):
      group_start = i * group_size
      group_end = (i + 1) * group_size
      group = Lambda(lambda x: x[:, :, group_start: group_end])(x)
      group = Conv1D(
          num_filters_per_group, k, use_bias=False,
          padding=padding, dilation_rate=dilation_rate)(group)
      group = BatchNormalization()(group)
      group = Activation(relu6)(group)
      groups.append(group)
    if g == 1:
      return groups[0]
    return Concatenate()(groups)

  input_layer = Input(shape=[98 * 257])
  x = input_layer
  x = PreprocessRaw(x)
  x = Reshape([98, 257])(x)
  x = _grouped_reduce_conv(x, 300, 3, 4, 252)  # 48
  x = _grouped_context_conv(x, 300, 3, 3, 300)
  x = _grouped_reduce_conv(x, 360, 3, 4, 300)  # 22
  x = _grouped_context_conv(x, 360, 3, 3, 360)
  x = _grouped_reduce_conv(x, 420, 3, 4, 360)  # 9
  x = _grouped_context_conv(x, 420, 3, 3, 360)
  x = _grouped_reduce_conv(x, 480, 3, 4, 420)  # 3
  x = _grouped_context_conv(x, 480, 3, 3, 480)
  x = Flatten()(x)
  x = Dropout(0.3)(x)
  x = Dense(num_classes, activation='softmax')(x)

  model = Model(input_layer, x, name='conv_1d_spec')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=2e-3),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_top_down_model(input_size=16000, num_classes=11):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  def _grouped_reduce_conv(x, num_filters, k, g, num_channels,
                           strides=2, padding='valid'):
    groups = []
    assert g >= 1
    assert num_channels % g == 0
    assert num_filters % g == 0
    group_size = int(num_channels / g)
    num_filters_per_group = int(num_filters / g)
    for i in range(g):
      group_start = i * group_size
      group_end = (i + 1) * group_size
      group = Lambda(lambda x: x[:, :, group_start: group_end])(x)
      group = _depthwise_conv_block(
          group, num_filters_per_group, k, padding=padding, use_bias=False,
          strides=strides)
      groups.append(group)
    if g == 1:
      return groups[0]
    return Concatenate()(groups)

  def _grouped_context_conv(x, num_filters, k, g, num_channels,
                            dilation_rate=1, padding='valid'):
    groups = []
    assert g >= 1
    assert num_channels % g == 0
    assert num_filters % g == 0
    group_size = int(num_channels / g)
    num_filters_per_group = int(num_filters / g)
    for i in range(g):
      group_start = i * group_size
      group_end = (i + 1) * group_size
      group = Lambda(lambda x: x[:, :, group_start: group_end])(x)
      group = _depthwise_conv_block(
          x, num_filters_per_group, k, use_bias=False,
          padding=padding, dilation_rate=dilation_rate)
      groups.append(group)
    if g == 1:
      return groups[0]
    return Concatenate()(groups)

  input_layer = Input(shape=[input_size])
  x = input_layer
  x = PreprocessRaw(x)
  x = Reshape([-1, 1])(x)
  x = Conv1D(480, 479, strides=160)(x)  # 98
  x = _grouped_reduce_conv(x, 420, 3, 3, 480)  # 48
  x = _grouped_context_conv(x, 420, 3, 2, 420)
  x = _grouped_reduce_conv(x, 360, 3, 3, 300)  # 22
  x = _grouped_context_conv(x, 360, 3, 2, 360)
  x = _grouped_reduce_conv(x, 300, 3, 3, 360)  # 9
  x = _grouped_context_conv(x, 300, 3, 2, 300)
  x = _grouped_reduce_conv(x, 240, 3, 3, 300)  # 3
  x = _grouped_context_conv(x, 240, 3, 2, 240)
  x = Flatten()(x)
  x = Dropout(0.05)(x)
  x = Dense(num_classes, activation='softmax')(x)

  model = Model(input_layer, x, name='conv_1d_top_down')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=3e-3),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_log_mfcc_model(
        input_size=16000, num_classes=11, *args, **kwargs):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = True.
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  time_size = kwargs.get('spectrogram_length', 65)
  frequency_size = kwargs.get('num_log_mel_features', 40)

  def _reduce_conv(x, num_filters, k, strides=2, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, use_bias=False, strides=strides)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, dilation_rate=dilation_rate,
        use_bias=False)
    return x

  def _reduce_block(x, num_filters, k):
    x = _reduce_conv(x, num_filters, k, padding='same')
    x = _context_conv(x, num_filters, k, padding='valid')
    return x

  def _residual_block(x, num_filters, k, strides=1, padding='same'):
    if strides != 1:
      residual = Conv1D(
          num_filters, 1, strides=strides, padding='same', use_bias=False)(x)
      residual = BatchNormalization()(residual)
    else:
      residual = x
    x = _depthwise_conv_block(
        x, num_filters, k, padding='same', use_bias=False)
    x = _depthwise_conv_block(
        x, num_filters, k, padding='same', use_bias=False)
    x = MaxPool1D(pool_size=strides, strides=strides, padding='same')(x)
    return Add()([x, residual])

  input_layer = Input(shape=[input_size])
  x = input_layer
  x = Reshape([time_size, frequency_size])(x)
  # default conv
  x = Conv1D(64, 3, use_bias=False,
             kernel_regularizer=l2(1e-5))(x)
  x = BatchNormalization()(x)
  x = Activation(relu6)(x)
  # depthwise conv
  x = _residual_block(x, 64, 3)
  x = _residual_block(x, 64, 3)
  x = _residual_block(x, 128, 3, strides=2)
  x = _residual_block(x, 128, 3)
  x = _residual_block(x, 192, 3, strides=2)
  x = _residual_block(x, 192, 3)
  x = _residual_block(x, 192, 3)
  x = _residual_block(x, 256, 3, strides=2)
  x = _residual_block(x, 256, 3)
  x = _residual_block(x, 256, 3)

  # attention before recurrent unit
  attention = _context_conv(x, 1, 3, padding='same')
  attention = Lambda(lambda x: softmax(x, axis=1))(attention)
  x = Multiply()([x, attention])
  # x = Bidirectional(GRU(128, kernel_regularizer=l2(1e-5),
  #                       dropout=0.2, recurrent_dropout=0.2))(x)
  x = GlobalAveragePooling1D()(x)
  x = Dropout(0.2)(x)
  x = Dense(num_classes, activation='softmax',
            kernel_regularizer=l2(1e-5))(x)

  model = Model(input_layer, x, name='conv_1d_log_mfcc')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=6e-4),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_spectrogram_model(
        input_size=16000, num_classes=11, *args, **kwargs):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = True.
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  time_size = kwargs.get('spectrogram_length', 65)
  frequency_size = kwargs.get('spectrogram_frequencies', 257)

  def _reduce_conv(x, num_filters, k, strides=2, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, use_bias=False, strides=strides)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, dilation_rate=dilation_rate,
        use_bias=False)
    return x

  def _reduce_block(x, num_filters, k):
    x = _reduce_conv(x, num_filters, k, padding='same')
    x = _context_conv(x, num_filters, k, padding='valid')
    return x

  def _residual_block(x, num_filters, k, strides=1, padding='same'):
    if strides != 1:
      residual = Conv1D(
          num_filters, 1, strides=strides, padding='same', use_bias=False)(x)
      residual = BatchNormalization()(residual)
    else:
      residual = x
    x = _depthwise_conv_block(
        x, num_filters, k, padding='same', use_bias=False)
    x = _depthwise_conv_block(
        x, num_filters, k, padding='same', use_bias=False)
    x = MaxPool1D(pool_size=strides, strides=strides, padding='same')(x)
    return Add()([x, residual])

  input_layer = Input(shape=[input_size])
  x = input_layer
  x = Reshape([time_size, frequency_size])(x)
  # default conv
  x = Conv1D(64, 3, use_bias=False,
             kernel_regularizer=l2(1e-5))(x)
  x = BatchNormalization()(x)
  x = Activation(relu6)(x)
  # depthwise conv
  x = _residual_block(x, 64, 3)
  x = _residual_block(x, 64, 3)
  x = _residual_block(x, 128, 3, strides=2)
  x = _residual_block(x, 128, 3)
  x = _residual_block(x, 192, 3, strides=2)
  x = _residual_block(x, 192, 3)
  x = _residual_block(x, 192, 3)
  x = _residual_block(x, 256, 3, strides=2)
  x = _residual_block(x, 256, 3)
  x = _residual_block(x, 256, 3)

  # attention before recurrent unit
  attention = _context_conv(x, 1, 3, padding='same')
  attention = Lambda(lambda x: softmax(x, axis=1))(attention)
  x = Multiply()([x, attention])
  # x = Bidirectional(GRU(128, kernel_regularizer=l2(1e-5),
  #                       dropout=0.2, recurrent_dropout=0.2))(x)
  x = GlobalAveragePooling1D()(x)
  x = Dropout(0.2)(x)
  x = Dense(num_classes, activation='softmax',
            kernel_regularizer=l2(1e-5))(x)

  model = Model(input_layer, x, name='conv_1d_spectrogram')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=3e-4),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def conv_1d_mfcc_and_raw_model(
        input_size=16000, num_classes=11, *args, **kwargs):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = True.
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  time_size = kwargs.get('spectrogram_length', 65)
  frequency_size = kwargs.get('num_log_mel_features', 40)
  raw_size = kwargs.get('desired_samples', 16000)
  frame_length = kwargs.get('window_size_samples', 480)
  frame_step = kwargs.get('window_stride_samples', 160)

  def _reduce_conv(x, num_filters, k, strides=2, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, use_bias=False, strides=strides)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, dilation_rate=dilation_rate,
        use_bias=False)
    return x

  def _reduce_block(x, num_filters, k):
    x = _reduce_conv(x, num_filters, k, padding='same')
    x = _context_conv(x, num_filters, k, padding='valid')
    return x

  def _residual_block(x, num_filters, k, strides=1, padding='same'):
    if strides != 1:
      residual = Conv1D(
          num_filters, 1, strides=strides, padding='same', use_bias=False)(x)
      residual = BatchNormalization()(residual)
    else:
      residual = x
    x = _depthwise_conv_block(
        x, num_filters, k, padding='same', use_bias=False)
    x = _depthwise_conv_block(
        x, num_filters, k, padding='same', use_bias=False)
    x = MaxPool1D(pool_size=3, strides=strides, padding='same')(x)
    return Add()([x, residual])

  # mfcc features
  input_layer_mfcc = Input(shape=[input_size])
  x_mfcc = input_layer_mfcc
  x_mfcc = Reshape([time_size, frequency_size])(x_mfcc)
  # default conv
  x_mfcc = Conv1D(64, 3, use_bias=False,
                  kernel_regularizer=l2(1e-5))(x_mfcc)
  x_mfcc = BatchNormalization()(x_mfcc)
  x_mfcc = Activation(relu6)(x_mfcc)
  # raw features
  input_layer_raw = Input(shape=[raw_size])
  x_raw = input_layer_raw
  x_raw = Lambda(lambda x: overlapping_time_slice_stack(
      x, frame_length, frame_step, padding='VALID'))(x_raw)
  # default conv
  x_raw = Conv1D(96, 3, use_bias=False,
                 kernel_regularizer=l2(1e-5))(x_raw)
  x_raw = BatchNormalization()(x_raw)
  x_raw = Activation(relu6)(x_raw)

  # depthwise conv
  x = Concatenate()([x_mfcc, x_raw])
  x = _residual_block(x, 160, 3)
  x = _residual_block(x, 160, 3)
  x = _residual_block(x, 192, 3, strides=2)
  x = _residual_block(x, 192, 3)
  x = _residual_block(x, 256, 3, strides=2)
  x = _residual_block(x, 256, 3)
  x = _residual_block(x, 320, 3, strides=2)
  x = _residual_block(x, 320, 3)
  x = _residual_block(x, 384, 3, strides=2)
  x = _residual_block(x, 384, 3)

  # attention before recurrent unit
  # attention = _context_conv(x, 1, 3, padding='same')
  # attention = Lambda(lambda x: softmax(x, axis=1))(attention)
  # x = Multiply()([x, attention])
  # x = Bidirectional(GRU(128, kernel_regularizer=l2(1e-5),
  #                       dropout=0.2, recurrent_dropout=0.2))(x)
  x = GlobalAveragePooling1D()(x)
  x = Dropout(0.3)(x)
  x = Dense(num_classes, activation='softmax',
            kernel_regularizer=l2(1e-5))(x)

  model = Model([input_layer_mfcc, input_layer_raw],
                x, name='conv_1d_mfcc_and_raw')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=5e-4),
      loss=keras.losses.categorical_crossentropy,
      metrics=[keras.metrics.categorical_accuracy])
  return model


def steffeNet(input_size=16000, num_classes=11, *args, **kwargs):
  """ Creates a 1D model for temporal data. Note: Use only
  with compute_mfcc = False (e.g. raw waveform data).
  Args:
    input_size: How big the input vector is.
    num_classes: How many classes are to be recognized.
  Returns:
    Compiled keras model
  """
  def _reduce_conv(x, num_filters, k, strides=2, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, use_bias=False, strides=strides)
    return x

  def _context_conv(x, num_filters, k, dilation_rate=1, padding='valid'):
    x = _depthwise_conv_block(
        x, num_filters, k, padding=padding, dilation_rate=dilation_rate,
        use_bias=False)
    return x

  def _reduce_block(x, num_filters, k):
    x = _reduce_conv(x, num_filters, k, padding='same')
    x = _context_conv(x, num_filters, k, padding='valid')
    return x

  def _residual_block(x, num_filters, k, strides=1, padding='same'):
    if strides != 1:
      residual = Conv1D(
          num_filters, 1, strides=strides, padding='same', use_bias=False)(x)
      residual = BatchNormalization()(residual)
    else:
      residual = x
    x = _depthwise_conv_block(
        x, num_filters, k, strides=strides, padding='same', use_bias=False)
    x = _depthwise_conv_block(
        x, num_filters, k, padding='same', use_bias=False)
    return Add()([x, residual])

  input_layer = Input(shape=[input_size])
  x = input_layer
  # add channel dimension
  x = Reshape([-1, 1])(x)
  x = Conv1D(256, 75, strides=50, padding='same', use_bias=False)(x)
  x = BatchNormalization()(x)
  x = Activation(relu6)(x)
  x = _context_conv(x, 256, 3, padding='same')
  for nh in [320, 384, 512, 768, 1024, 1536]:
    x = _residual_block(x, nh, 3, strides=2)
    x = _residual_block(x, nh, 3)

  x_max = GlobalMaxPooling1D()(x)
  x_avg = GlobalAveragePooling1D()(x)
  x = Concatenate()([x_max, x_avg])
  x = Dropout(0.5)(x)
  x = Dense(num_classes, activation='softmax', use_bias=False,
            kernel_regularizer=l2(1e-5))(x)

  model = Model(input_layer, x, name='steffeNet')
  model.compile(
      optimizer=keras.optimizers.RMSprop(lr=1.0e-3),
      loss=lambda y_true, y_pred: smooth_categorical_crossentropy(
          y_true, y_pred, label_smoothing=0.1),
      metrics=[keras.metrics.categorical_accuracy])
  return model


def speech_model(model_type, input_size, num_classes=11, *args, **kwargs):
  if model_type == 'simple':
    return simple_model(input_size, num_classes)
  elif model_type == 'snn':
    return snn_model(input_size, num_classes)
  elif model_type == 'conv_1d_time_stacked':
    return conv_1d_time_stacked_model(input_size, num_classes)
  elif model_type == 'conv_1d_multi_time_sliced':
    return conv_1d_multi_time_sliced_model(input_size, num_classes)
  elif model_type == 'conv_1d_time_sliced':
    return conv_1d_time_sliced_model(input_size, num_classes)
  elif model_type == 'conv_1d_time_sliced_group':
    return conv_1d_time_sliced_group_model(input_size, num_classes)
  elif model_type == 'conv_1d_heavy':
    return conv_1d_heavy_model(input_size, num_classes)
  elif model_type == 'conv_1d_simple':
    return conv_1d_simple_model(input_size, num_classes)
  elif model_type == 'conv_1d_gru':
    return conv_1d_gru_model(input_size, num_classes)
  elif model_type == 'conv_2d':
    return conv_2d_model(input_size, num_classes)
  elif model_type == 'conv_2d_fast':
    return conv_2d_fast_model(input_size, num_classes)
  elif model_type == 'conv_2d_mobile':
    return conv_2d_mobile_model(input_size, num_classes)
  elif model_type == 'inception':
    return conv_1d_inception_model(input_size, num_classes)
  elif model_type == 'inception_d1':
    return conv_inception_d1_model(input_size, num_classes)
  elif model_type == 'conv_1d_learned_spec':
    return conv_1d_learned_spec_model(input_size, num_classes)
  elif model_type == 'conv_1d_spec':
    return conv_1d_spec_model(input_size, num_classes)
  elif model_type == 'conv_1d_fast':
    return conv_1d_fast_model(input_size, num_classes)
  elif model_type == 'conv_1d_top_down':
    return conv_1d_top_down_model(input_size, num_classes)
  elif model_type == 'conv_1d_residual':
    return conv_1d_residual_model(input_size, num_classes)
  elif model_type == 'xception_with_attention':
    return xception_with_attention_model(input_size, num_classes)
  elif model_type == 'conv_1d_time_sliced_with_attention':
    return conv_1d_time_sliced_with_attention_model(input_size, num_classes)
  elif model_type == 'conv_1d_log_mfcc':
    return conv_1d_log_mfcc_model(input_size, num_classes, *args, **kwargs)
  elif model_type == 'conv_1d_spectrogram':
    return conv_1d_spectrogram_model(input_size, num_classes, *args, **kwargs)
  elif model_type == 'conv_1d_mfcc_and_raw':
    return conv_1d_mfcc_and_raw_model(input_size, num_classes, *args, **kwargs)
  elif model_type == 'steffeNet':
    return steffeNet(input_size, num_classes, *args, **kwargs)
  else:
    raise ValueError("Invalid model: %s" % model_type)


# from here: https://github.com/tensorflow/tensorflow/blob/master/tensorflow/examples/speech_commands/models.py  # noqa
def prepare_model_settings(label_count, sample_rate, clip_duration_ms,
                           window_size_ms, window_stride_ms,
                           dct_coefficient_count, num_log_mel_features,
                           output_representation='raw'):
  """Calculates common settings needed for all models.
  Args:
    label_count: How many classes are to be recognized.
    sample_rate: Number of audio samples per second.
    clip_duration_ms: Length of each audio clip to be analyzed.
    window_size_ms: Duration of frequency analysis window.
    window_stride_ms: How far to move in time between frequency windows.
    dct_coefficient_count: Number of frequency bins to use for analysis.
  Returns:
    Dictionary containing common settings.
  """
  desired_samples = int(sample_rate * clip_duration_ms / 1000)
  window_size_samples = int(sample_rate * window_size_ms / 1000)
  window_stride_samples = int(sample_rate * window_stride_ms / 1000)
  length_minus_window = (desired_samples - window_size_samples)
  spectrogram_frequencies = 257
  if length_minus_window < 0:
    spectrogram_length = 0
  else:
    spectrogram_length = 1 + int(length_minus_window / window_stride_samples)
  if output_representation == 'mfcc':
    fingerprint_size = num_log_mel_features * spectrogram_length
  elif output_representation == 'raw':
    fingerprint_size = desired_samples
  elif output_representation == 'spec':
    fingerprint_size = spectrogram_frequencies * spectrogram_length
  elif output_representation == 'mfcc_and_raw':
    fingerprint_size = num_log_mel_features * spectrogram_length
  return {
      'desired_samples': desired_samples,
      'window_size_samples': window_size_samples,
      'window_stride_samples': window_stride_samples,
      'spectrogram_length': spectrogram_length,
      # TODO(see--): Check where this comes from
      'spectrogram_frequencies': spectrogram_frequencies,
      'dct_coefficient_count': dct_coefficient_count,
      'fingerprint_size': fingerprint_size,
      'label_count': label_count,
      'sample_rate': sample_rate,
      'num_log_mel_features': num_log_mel_features
  }
