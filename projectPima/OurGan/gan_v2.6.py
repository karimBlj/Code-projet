import matplotlib as mpl

# This line allows mpl to run with no DISPLAY defined
#mpl.use('Agg')

import numpy
#import preprocess
import matplotlib.pyplot as plt
import matplotlib as mtl
import gzip
import pickle
from keras.layers import Flatten, Dropout, LeakyReLU, Input, Activation
from keras.models import Model
from keras.layers.convolutional import UpSampling2D
from keras.optimizers import Adam
from keras.datasets import mnist
import pandas as pd
import numpy as np
import keras.backend as K
from keras_adversarial.legacy import Dense, BatchNormalization, Convolution2D
from keras_adversarial.image_grid_callback import ImageGridCallback
from keras_adversarial import AdversarialModel, simple_gan, gan_targets
from keras_adversarial import AdversarialOptimizerSimultaneous, normal_latent_sampling
from image_utils import dim_ordering_fix, dim_ordering_input, dim_ordering_reshape, dim_ordering_unfix


def leaky_relu(x):
    return K.relu(x, 0.2)


def model_generator():
    nch = 256
    g_input = Input(shape=[200])
    H = Dense(nch * 14 * 14)(g_input)
    H = BatchNormalization(mode=2)(H)
    H = Activation('relu')(H)
    H = dim_ordering_reshape(nch, 14)(H)
    H = UpSampling2D(size=(2, 2))(H)
    H = Convolution2D(int(nch / 2), 3, 3, border_mode='same')(H)
    H = BatchNormalization(mode=2, axis=1)(H)
    H = Activation('relu')(H)
    H = Convolution2D(int(nch / 4), 3, 3, border_mode='same')(H)
    H = BatchNormalization(mode=2, axis=1)(H)
    H = Activation('relu')(H)
    H = Convolution2D(1, 1, 1, border_mode='same')(H)
    g_V = Activation('sigmoid')(H)
    return Model(g_input, g_V)


def model_discriminator(input_shape=(1, 28, 28), dropout_rate=0.5):
    d_input = dim_ordering_input(input_shape, name="input_x")
    nch = 256
    # nch = 128
    H = Convolution2D(int(nch / 2), 5, 5, subsample=(2, 2), border_mode='same', activation='relu')(d_input)
    H = LeakyReLU(0.2)(H)
    H = Dropout(dropout_rate)(H)
    H = Convolution2D(nch, 5, 5, subsample=(2, 2), border_mode='same', activation='relu')(H)
    H = LeakyReLU(0.2)(H)
    H = Dropout(dropout_rate)(H)
    H = Flatten()(H)
    H = Dense(int(nch / 2))(H)
    H = LeakyReLU(0.2)(H)
    H = Dropout(dropout_rate)(H)
    d_V = Dense(1, activation='sigmoid')(H)
    return Model(d_input, d_V)


def mnist_process(x):
    x = x.astype(np.float32) / 255.0
    return x


def mnist_data():
    (xtrain, ytrain), (xtest, ytest) = mnist.load_data()
    return mnist_process(xtrain), mnist_process(xtest)


def generator_sampler(latent_dim, generator):
    def fun():
        zsamples = np.random.normal(size=(10 * 10, latent_dim))
        gen = dim_ordering_unfix(generator.predict(zsamples))
        return gen.reshape((10, 10, 28, 28))

    return fun

def generator_skampler(latent_dim, generator):
    zsamples = np.random.normal(size=(10 * 10, latent_dim))
    gen = dim_ordering_unfix(generator.predict(zsamples))
    return gen.reshape((10, 10, 28, 28))

    
if __name__ == "__main__":
    # z \in R^100
    latent_dim = 200
    # x \in R^{28x28}
    input_shape = (1, 28, 28)

    # generator (z -> x)
    generator = model_generator()
    # discriminator (x -> y)
    discriminator = model_discriminator(input_shape=input_shape)
    # gan (x - > yfake, yreal), z generated on GPU
    gan = simple_gan(generator, discriminator, normal_latent_sampling((latent_dim,)))

    # print summary of models
    generator.summary()
    discriminator.summary()
    gan.summary()

    # build adversarial model
    model = AdversarialModel(base_model=gan,
                             player_params=[generator.trainable_weights, discriminator.trainable_weights],
                             player_names=["generator", "discriminator"])
    model.adversarial_compile(adversarial_optimizer=AdversarialOptimizerSimultaneous(),
                              player_optimizers=[Adam(1e-4, decay=1e-4), Adam(1e-3, decay=1e-4)],
                              loss='binary_crossentropy')

    # train model
    generator_cb = ImageGridCallback("output/gan_convolutional/epoch-{:03d}.png",
                                     generator_sampler(latent_dim, generator))

    fname = "base_hiver_2008.pklgz"
    with gzip.open(fname, "rb") as fp:
        dictio = pickle.load(fp)
    
    data = dictio['SSTMW']
    x = data[:,:28,:28].astype(np.float32)
    xtrain = x[:-10]
    xtest = x[-10:]
    
    mini = np.min(xtrain.ravel())
    maxi = np.max(xtrain.ravel())
    xtrain = (xtrain - mini)/(maxi-mini)
    xtest = (xtest-mini)/(maxi-mini)
    
    
    xtrain = dim_ordering_fix(xtrain.reshape((-1, 1, 28, 28)))
    xtest = dim_ordering_fix(xtest.reshape((-1, 1, 28, 28)))


          
    y = gan_targets(xtrain.shape[0])
    ytest = gan_targets(xtest.shape[0])
    history = model.fit(x=xtrain, y=y, validation_data=(xtest, ytest), callbacks=[generator_cb], nb_epoch=1,
                        batch_size=10)
    df = pd.DataFrame(history.history)
    df.to_csv("output/gan_convolutional/history.csv")

    generator.save("output/gan_convolutional/generator.h5")
    discriminator.save("output/gan_convolutional/discriminator.h5")


    #  print(xtrain[0])
    """
    print(xtest[0])
    """

    
    yy = generator_skampler(latent_dim, generator)

    mtl.use("gtk")
    plt.ion()
    print(yy[0][0])
    plt.imshow(yy[0][0])
    #plt.plot(yy[0][0])
    plt.show()
"""
    fi = open("pictures.txt", "wb")
    fi.printf(yy[0][0])
    fi.printf(yy[0][1])
    fi.printf(yy[0][2])
    fi.printf(yy[0])
"""