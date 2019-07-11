#!/usr/bin/env python
# coding: utf-8

import tensorflow as tf
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import random
import shutil
from scipy.special import expit
import tensorflow.contrib.learn as tflearn
import tensorflow.contrib.layers as tflayers
from tensorflow.contrib.learn.python.learn import learn_runner
import tensorflow.contrib.metrics as metrics
import tensorflow.contrib.rnn as rnn

file_name = './notebooks/historic_data/BTC-USD_300_200173.csv'
window = 288 # 1 day
# Read csv, use Time column as a datetime index, and sort by this index
df = pd.read_csv(file_name, index_col='Time', parse_dates=True, infer_datetime_format=True).sort_index()
# Resample the data to a longer time interval, keeping the OHLCV data correct
#df = df.resample('15Min').apply({'Open' : 'first', 'High' : 'max', 'Low' : 'min', 'Close' : 'last', 'Volume' : 'sum'})
# Calculate the Oracle stance
df['Stance'] = df['Close'].rolling(window=window,center=True).mean().diff().rolling(window=window,center=True).mean()
# https://stackoverflow.com/questions/31287552/logarithmic-returns-in-pandas-dataframe
#df['CloseGrossReturn'] = df['Close'].pct_change()
df['CloseLogReturn'] = np.log(df['Close'] / df['Close'].shift(1))
# Scale a column to have variance of 1, do not shift the mean
#df['CloseReturnVNorm'] = scale(df['CloseLogReturn'].values, with_mean=False)
#df['CloseReturnMMNorm'] = minmax_scale(df['CloseLogReturn'].values, feature_range=(0, 1))
#df['CloseReturnRNorm'] = robust_scale(df['CloseLogReturn'].values, with_centering=False)

#df['VolumeMMNorm'] = minmax_scale(df['Volume'].values, feature_range=(0, 1))
#df['StanceVNorm'] = scale(df['Stance'].values, with_mean=False)
#df['StanceMMNorm'] = minmax_scale(df['Stance'].values, feature_range=(0, 1))

df['StanceTanh'] = np.tanh(df['Stance'])
df['VolumnSigm'] = expit(df['Volume'])

# Create categorical columns from some aspect of the time
df = pd.concat([df, pd.get_dummies(df.index.weekday, prefix='DayOfWeek').set_index(df.index)], axis=1)
df = pd.concat([df, pd.get_dummies(df.index.hour, prefix='HourOfDay').set_index(df.index)], axis=1)
#df.dropna(inplace=True)
#df[-7000:-6000].plot(y=['StanceMMNorm', 'CloseReturnMMNorm', 'VolumeMMNorm'], secondary_y=['CloseReturnMMNorm'], figsize=(15, 5), grid=True)
#df[-6500:-6000].plot(y=['StanceVNorm', 'CloseReturnRNorm', 'VolumeMMNorm'],figsize=(15, 5), grid=True)

df.describe()


# In[6]:


cols = ['CloseLogReturn', 'VolumnSigm']

X1=np.array(df['CloseLogReturn'])
X2=np.array(df['VolumnSigm'])

Y=np.array(df['StanceTanh'])

sequence_length = 288 * 7 # One Week
test_periods = 4

x1_data = X1[:(len(X1) - test_periods * sequence_length - (len(X1) % sequence_length))]
x2_data = X2[:(len(X2) - test_periods * sequence_length - (len(X2) % sequence_length))]
x_data = np.dstack([x1_data, x2_data])

x_batches = x_data.reshape(-1, sequence_length, 2)

y_data = Y[:(len(Y) - test_periods * sequence_length - (len(Y) % sequence_length))]
y_batches = y_data.reshape(-1, sequence_length, 1)

print(x_batches.shape)
print(y_batches.shape)


# In[7]:


testX1 = X1[-(test_periods*sequence_length):]
testX2 = X2[-(test_periods*sequence_length):]
testX = np.dstack([testX1, testX2]).reshape(-1, sequence_length, 2)
testY = Y[-(test_periods*sequence_length):].reshape(-1, sequence_length, 1)
print(testX.shape)
print(testY.shape)


# In[8]:


tf.reset_default_graph()

input_s = 2
hidden = 256
output_s = 1
learning_rate = 0.001

x = tf.placeholder(tf.float32, [None, sequence_length, input_s])
y = tf.placeholder(tf.float32, [None, sequence_length, output_s])

basic_cell = tf.nn.rnn_cell.LSTMCell(num_units=hidden)
rnn_output, states = tf.nn.dynamic_rnn(basic_cell, x, dtype=tf.float32)
rnn_output = tf.reshape(rnn_output, [-1, hidden])
outputs = tf.layers.dense(rnn_output, output_s)
outputs = tf.reshape(outputs, [-1, sequence_length, output_s])

loss = tf.losses.mean_squared_error(y, outputs)
optimiser = tf.train.AdamOptimizer(learning_rate=learning_rate)
training_op = optimiser.minimize(loss)

saver = tf.train.Saver()
init = tf.global_variables_initializer()


# In[ ]:


epochs = 10

checkpoint_path = "/home/richie/repo/twisty/dev/notebooks/cpts/512u80000p.ckpt"
continue_training = False

with tf.Session() as sess:
    init.run()
    if continue_training and tf.train.checkpoint_exists(checkpoint_path):
        saver.restore(sess, checkpoint_path)
        print("Model {} restored.".format(checkpoint_path))
    for ep in range(epochs):
        _, train_loss = sess.run((training_op, loss), feed_dict={x: x_batches, y: y_batches})
        mse = loss.eval(feed_dict={x: testX, y: testY})
        print("{}\tTrain Loss: {}\tTest Loss: {}".format(ep, train_loss * 4, mse * 35))
        save_path = saver.save(sess, checkpoint_path)
            
    # Save the variables to disk.
    save_path = saver.save(sess, checkpoint_path)
    print("Model saved in path: %s" % save_path)


