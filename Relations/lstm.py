#!/usr/bin/env python

import numpy as np
np.random.seed(1337)

import sys
sys.path.append('../Lib/')
sys.dont_write_bytecode = True

import sklearn as sk
from sklearn.metrics import f1_score
import keras as k
from keras.utils.np_utils import to_categorical
from keras.optimizers import RMSprop
from keras.preprocessing.sequence import pad_sequences
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation
from keras.layers.embeddings import Embedding
from keras.layers import LSTM
import ConfigParser, os
import dataset

if __name__ == "__main__":

  cfg = ConfigParser.ConfigParser()
  cfg.read(sys.argv[1])
  base = os.environ['DATA_ROOT']
  train_file = os.path.join(base, cfg.get('data', 'train'))
  test_file = os.path.join(base, cfg.get('data', 'test'))
  print 'train:', train_file
  print 'test:', test_file
  print 'batch:', cfg.get('lstm', 'batch')
  print 'epochs:', cfg.get('lstm', 'epochs')
  print 'embdims:', cfg.get('lstm', 'embdims')
  print 'units:', cfg.get('lstm', 'units')
  print 'dropout:', cfg.get('lstm', 'dropout')
  print 'udropout:', cfg.get('lstm', 'udropout')
  print 'wdropout:', cfg.get('lstm', 'wdropout')
  print 'learnrt:', cfg.get('lstm', 'learnrt')
  
  # learn alphabet from training examples
  dataset = dataset.DatasetProvider(train_file)
  # now load training examples and labels
  train_x, train_y = dataset.load(train_file)
  maxlen = max([len(seq) for seq in train_x])
  # now load test examples and labels
  test_x, test_y = dataset.load(test_file, maxlen=maxlen)

  # turn x and y into numpy array among other things
  classes = len(set(train_y))
  train_x = pad_sequences(train_x, maxlen=maxlen)
  train_y = to_categorical(np.array(train_y), classes)  
  test_x = pad_sequences(test_x, maxlen=maxlen)
  test_y = to_categorical(np.array(test_y), classes)  

  print 'train_x shape:', train_x.shape
  print 'train_y shape:', train_y.shape
  print 'test_x shape:', test_x.shape
  print 'test_y shape:', test_y.shape
  
  model = Sequential()
    
  model.add(Embedding(len(dataset.word2int),
                      cfg.getint('lstm', 'embdims'),
                      input_length=maxlen,
                      dropout=cfg.getfloat('lstm', 'dropout')))
  model.add(LSTM(cfg.getint('lstm', 'units'),
                 dropout_W = cfg.getfloat('lstm', 'wdropout'),
                 dropout_U = cfg.getfloat('lstm', 'udropout')))
  model.add(Dense(classes))
  model.add(Activation('softmax'))

  optimizer = RMSprop(lr=cfg.getfloat('lstm', 'learnrt'),
                      rho=0.9, epsilon=1e-08)
  model.compile(loss='categorical_crossentropy',
                optimizer=optimizer,
                metrics=['accuracy'])
  model.fit(train_x,
            train_y,
            nb_epoch=cfg.getint('lstm', 'epochs'),
            batch_size=cfg.getint('lstm', 'batch'),
            verbose=1,
            validation_split=0.1)

  # distribution over classes
  distribution = \
    model.predict(test_x, batch_size=cfg.getint('lstm', 'batch'))
  # class predictions
  predictions = np.argmax(distribution, axis=1)
  # gold labels
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
