from keras.models import Sequential
from keras.layers import LSTM, TimeDistributed, RepeatVector, Dense, Embedding
import numpy as np
import pandas as pd
# import wandb
# from wandb.keras import WandbCallback

# wandb.init()
# config = wandb.config


# class CharacterTable(object):
#     """Given a set of characters:
#     + Encode them to a one hot integer representation
#     + Decode the one hot integer representation to their character output
#     + Decode a vector of probabilities to their character output
#     """
#
#     def __init__(self, chars):
#         """Initialize character table.
#         # Arguments
#             chars: Characters that can appear in the input.
#         """
#         self.chars = sorted(set(chars))
#         self.char_indices = dict((c, i) for i, c in enumerate(self.chars))
#         self.indices_char = dict((i, c) for i, c in enumerate(self.chars))
#
#     def encode(self, C, num_rows):
#         """One hot encode given string C.
#         # Arguments
#             num_rows: Number of rows in the returned one hot encoding. This is
#                 used to keep the # of rows for each data the same.
#         """
#         x = np.zeros((num_rows, len(self.chars)))
#         for i, c in enumerate(C):
#             x[i, self.char_indices[c]] = 1
#         return x
#
#     def decode(self, x, calc_argmax=True):
#         if calc_argmax:
#             x = x.argmax(axis=-1)
#         return ''.join(self.indices_char[x] for x in x)
#
#
# # Parameters for the model and dataset.
# config.training_size = 50000
# config.digits = 5
# config.hidden_size = 128
# config.batch_size = 128
#
# # Maximum length of input is 'int + int' (e.g., '345+678'). Maximum length of
# # int is DIGITS.
# maxlen = config.digits + 1 + config.digits
#
# # All the numbers, plus sign and space for padding.
# chars = '0123456789+- '
# ctable = CharacterTable(chars)
#

load = pd.read_pickle('Seq2Seq.pickle')
load

# X = []
# for x, users in enumerate(load):  # 2000 users
#     X.append([])  # New user
#     for y, weeks in enumerate(users):  # Each user has 50 weeks of data
#         X[x].append([])  # New week
#         for z, week in enumerate(weeks):  # Each week has [3-7] recipes per week
#             X[x][y].append([])  # New recipe
#             if z != len(weeks)-1:  # Don't use last week
#                 for item in week:
#                 temp = [0 if x != week-1 else 1 for x in range(50)]  # One-hot with vocab length
#                 X[x][y][z] = np.array(temp)
#             while len(X[x][y]) < 7:  # Padding recipe recommendation length
#                 X[x][y].append([0 for x in range(7)])
# Y = []
# for x, users in enumerate(X):
#     for y, weeks in enumerate(users):
#         if y != len(weeks)-1:  # Cant append week after last week sample
#             Y.append(np.array(X[x][y+1]))
#
#
# print('Generating data...')
#     seen.add(key)
#     # Pad the data with spaces such that it is always MAXLEN.
#     q = '{}-{}'.format(a, b)
#     query = q + ' ' * (maxlen - len(q))
#     ans = str(a - b)
#     # Answers can be of maximum size DIGITS + 1.
#     ans += ' ' * (config.digits + 1 - len(ans))
#
#     questions.append(query)
#     expected.append(ans)
#
# print('Total addition questions:', len(questions))
#
# print('Vectorization...')
# x = np.zeros((2000, 7, 50), dtype=np.bool)  # Samples, sequence length, vocab
# y = np.zeros((2000, 7, 50), dtype=np.bool)
# for i, sentence in enumerate(questions):
#     x[i] = ctable.encode(sentence, maxlen)
# for i, sentence in enumerate(expected):
#     y[i] = ctable.encode(sentence, config.digits + 1)
#
#
# split_at = len(x) - len(x) // 10
# (x_train, x_val) = x[:split_at], x[split_at:]
# (y_train, y_val) = y[:split_at], y[split_at:]
#
# model = Sequential()
# model.add(LSTM(20, input_shape=(7, len(chars))))
# model.add(RepeatVector(50 + 1))
# model.add(LSTM(20, return_sequences=True))
# model.add(TimeDistributed(Dense(len(chars), activation='softmax')))
# model.compile(loss='categorical_crossentropy',
#               optimizer='adam',
#               metrics=['accuracy'])
# model.summary()
#
# # Train the model each generation and show predictions against the validation
# # dataset.
# for iteration in range(1, 200):
#     print()
#     print('-' * 50)
#     print('Iteration', iteration)
#     model.fit(x_train, y_train,
#               batch_size=config.batch_size,
#               epochs=1,
#               validation_data=(x_val, y_val), callbacks=[WandbCallback()])
#     # Select 10 samples from the validation set at random so we can visualize
#     # errors.
#     for i in range(10):
#         ind = np.random.randint(0, len(x_val))
#         rowx, rowy = x_val[np.array([ind])], y_val[np.array([ind])]
#         preds = model.predict_classes(rowx, verbose=0)
#         q = ctable.decode(rowx[0])
#         correct = ctable.decode(rowy[0])
#         guess = ctable.decode(preds[0], calc_argmax=False)
#         print('Q', q, end=' ')
#         print('T', correct, end=' ')
#         if correct == guess:
#             print('☑', end=' ')
#         else:
#             print('☒', end=' ')
#         print(guess)

