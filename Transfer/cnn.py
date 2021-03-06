#!/usr/bin/env python

import numpy as np
np.random.seed(1337)

import sys
sys.path.append('../Lib/')
sys.dont_write_bytecode = True
import ConfigParser, os
import sklearn as sk
from sklearn.metrics import f1_score
import keras as k
from keras.utils.np_utils import to_categorical
from keras.optimizers import RMSprop
from keras.preprocessing.sequence import pad_sequences
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation
from keras.layers import Conv1D, GlobalMaxPooling1D
from keras.layers.embeddings import Embedding
import dataset
import word2vec

def print_config(cfg):
  """Print configuration settings"""

  print 'train:', cfg.get('data', 'train')
  print 'test:', cfg.get('data', 'test')
  if cfg.has_option('data', 'embed'):
    print 'embeddings:', cfg.get('data', 'embed')

  print 'batch:', cfg.get('cnn', 'batch')
  print 'epochs:', cfg.get('cnn', 'epochs')
  print 'embdims:', cfg.get('cnn', 'embdims')
  print 'filters:', cfg.get('cnn', 'filters')
  print 'filtlen:', cfg.get('cnn', 'filtlen')
  print 'hidden:', cfg.get('cnn', 'hidden')
  print 'dropout:', cfg.get('cnn', 'dropout')
  print 'learnrt:', cfg.get('cnn', 'learnrt')

if __name__ == "__main__":

  # settings file specified as command-line argument
  cfg = ConfigParser.ConfigParser()
  cfg.read(sys.argv[1])
  print_config(cfg)
  base = os.environ['DATA_ROOT']
  train_file = os.path.join(base, cfg.get('data', 'train'))
  test_file = os.path.join(base, cfg.get('data', 'test'))

  # learn alphabet from training examples
  dataset = dataset.DatasetProvider(train_file)
  # now load training examples and labels
  train_x, train_y = dataset.load(train_file)
  maxlen = max([len(seq) for seq in train_x])
  # now load test examples and labels
  test_x, test_y = dataset.load(test_file, maxlen=maxlen)

  init_vectors = None
  # TODO: what what are we doing for index 0 (oov words)?
  # use pre-trained word embeddings?
  if cfg.has_option('data', 'embed'):
    embed_file = os.path.join(base, cfg.get('data', 'embed'))
    w2v = word2vec.Model(embed_file)
    init_vectors = [w2v.select_vectors(dataset.word2int)]

  # turn x and y into numpy array among other things
  classes = len(set(train_y))
  train_x = pad_sequences(train_x, maxlen=maxlen)
  train_y = to_categorical(np.array(train_y), classes)
  test_x = pad_sequences(test_x, maxlen=maxlen)
  test_y = to_categorical(np.array(test_y), classes)

  print 'train_x shape:', train_x.shape
  print 'train_y shape:', train_y.shape
  print 'test_x shape:', test_x.shape
  print 'test_y shape:', test_y.shape, '\n'

  model = Sequential()
  model.add(Embedding(len(dataset.word2int),
                       cfg.getint('cnn', 'embdims'),
                       input_length=maxlen,
                       trainable=True,
                       weights=init_vectors))
  model.add(Conv1D(filters=cfg.getint('cnn', 'filters'),
                   kernel_size=cfg.getint('cnn', 'filtlen'),
                   activation='relu'))
  model.add(GlobalMaxPooling1D())

  model.add(Dropout(cfg.getfloat('cnn', 'dropout')))
  model.add(Dense(cfg.getint('cnn', 'hidden')))
  model.add(Activation('relu'))

  model.add(Dropout(cfg.getfloat('cnn', 'dropout')))
  model.add(Dense(classes))
  model.add(Activation('softmax'))

  optimizer = RMSprop(lr=cfg.getfloat('cnn', 'learnrt'))
  model.compile(loss='categorical_crossentropy',
                optimizer=optimizer,
                metrics=['accuracy'])
  model.fit(train_x,
            train_y,
            epochs=cfg.getint('cnn', 'epochs'),
            batch_size=cfg.getint('cnn', 'batch'),
            verbose=1,
            validation_split=0.0)

  # get_weights() returns a list of 1 element
  # dump these weights to file (word2vec model format)
  weights = model.layers[0].get_weights()[0]
  word2vec.write_vectors(dataset.word2int, weights, 'weights.txt')

  # probability for each class; (test size, num of classes)
  distribution = \
    model.predict(test_x, batch_size=cfg.getint('cnn', 'batch'))
  # class predictions; (test size,)
  predictions = np.argmax(distribution, axis=1)
  # gold labels; (test size,)
  gold = np.argmax(test_y, axis=1)

  # f1 scores
  label_f1 = f1_score(gold, predictions, average=None)

  print
  for label, idx in dataset.label2int.items():
    print 'f1(%s)=%f' % (label, label_f1[idx])

  if 'contains' in dataset.label2int:
    idxs = [dataset.label2int['contains'], dataset.label2int['contains-1']]
    contains_f1 = f1_score(gold, predictions, labels=idxs, average='micro')
    print '\nf1(contains average) =', contains_f1
  else:
    idxs = dataset.label2int.values()
    average_f1 = f1_score(gold, predictions, labels=idxs, average='micro')
    print 'f1(all) =', average_f1
