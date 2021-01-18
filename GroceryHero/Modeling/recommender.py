from keras.layers import Embedding, Dense, GlobalAvgPool1D
from keras import Sequential


def detr_loss(out=1):
    embeddings = 1
    dot = embeddings * out

    loss = None
    return loss


model = Sequential()
model.add(Embedding(1000, 80, input_length=10, input_shape=(10, 3)))
model.add(Dense(100, activation='relu'))
model.add(GlobalAvgPool1D())
model.add(Dense(100))
model.compile(optimizer='adam', loss='MSE')

