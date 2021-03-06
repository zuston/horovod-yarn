# Copyright 2019 Uber Technologies, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

import tensorflow as tf
import horovod.tensorflow as hvd

import os
from optparse import OptionParser
import sys

def setHorovodRuntimeEnv():
    parser = OptionParser()
    parser.add_option(
        "-p", "--port", dest="port", type="str", help="rendevous port")
    parser.add_option(
        "-r", "--rank", dest="rank", type="str"
    )
    parser.add_option(
        "-s", "--size", dest="size", type="str"
    )
    parser.add_option(
        "-a", "--local_rank", dest="local_rank", type="str"
    )
    parser.add_option(
        "-b", "--local_size", dest="local_size", type="str"
    )
    parser.add_option(
        "-c", "--cross_rank", dest="cross_rank", type="str"
    )
    parser.add_option(
        "-d", "--cross_size", dest="cross_size", type="str"
    )
    parser.add_option(
        "-e", "--timeout", dest="timeout", type="str", default="2000"
    )
    parser.add_option(
        "-t", action="store_true", help="enable elastic training.", dest="enable_elastic", default=False
    )

    (options, args) = parser.parse_args(sys.argv)
    
    os.environ['HOROVOD_GLOO_RENDEZVOUS_ADDR'] = 'localhost'
    os.environ['HOROVOD_GLOO_RENDEZVOUS_PORT'] = options.port
    os.environ['HOROVOD_CONTROLLER'] = 'gloo'
    os.environ['HOROVOD_CPU_OPERATIONS'] = 'gloo'

    os.environ['HOROVOD_HOSTNAME'] = 'localhost'
    os.environ['HOROVOD_RANK'] = options.rank
    os.environ['HOROVOD_SIZE'] = options.size
    os.environ['HOROVOD_LOCAL_RANK'] = options.local_rank
    os.environ['HOROVOD_LOCAL_SIZE'] = options.local_size
    os.environ['HOROVOD_CROSS_RANK'] = options.cross_rank
    os.environ['HOROVOD_CROSS_SIZE'] = options.cross_size

    os.environ['HOROVOD_GLOO_TIMEOUT_SECONDS'] = options.timeout

    if options.enable_elastic:
        os.environ['HOROVOD_ELASTIC'] = 1

def main():
    # Horovod: initialize Horovod.
    hvd.init()

    # Horovod: pin GPU to be used to process local rank (one GPU per process)
    # gpus = tf.config.experimental.list_physical_devices('GPU')
    # for gpu in gpus:
    #     tf.config.experimental.set_memory_growth(gpu, True)
    # if gpus:
    #     tf.config.experimental.set_visible_devices(gpus[hvd.local_rank()], 'GPU')

    (mnist_images, mnist_labels), _ = \
        tf.keras.datasets.mnist.load_data(path='mnist-%d.npz' % hvd.rank())

    dataset = tf.data.Dataset.from_tensor_slices(
        (tf.cast(mnist_images[..., tf.newaxis] / 255.0, tf.float32),
                tf.cast(mnist_labels, tf.int64))
    )
    dataset = dataset.repeat().shuffle(10000).batch(128)

    mnist_model = tf.keras.Sequential([
        tf.keras.layers.Conv2D(32, [3, 3], activation='relu'),
        tf.keras.layers.Conv2D(64, [3, 3], activation='relu'),
        tf.keras.layers.MaxPooling2D(pool_size=(2, 2)),
        tf.keras.layers.Dropout(0.25),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dropout(0.5),
        tf.keras.layers.Dense(10, activation='softmax')
    ])
    loss = tf.losses.SparseCategoricalCrossentropy()

    # Horovod: adjust learning rate based on number of GPUs.
    opt = tf.optimizers.Adam(0.001 * hvd.size())

    checkpoint_dir = './checkpoints'
    checkpoint = tf.train.Checkpoint(model=mnist_model, optimizer=opt)


    @tf.function
    def training_step(images, labels, first_batch):
        with tf.GradientTape() as tape:
            probs = mnist_model(images, training=True)
            loss_value = loss(labels, probs)

        # Horovod: add Horovod Distributed GradientTape.
        tape = hvd.DistributedGradientTape(tape)

        grads = tape.gradient(loss_value, mnist_model.trainable_variables)
        opt.apply_gradients(zip(grads, mnist_model.trainable_variables))

        # Horovod: broadcast initial variable states from rank 0 to all other processes.
        # This is necessary to ensure consistent initialization of all workers when
        # training is started with random weights or restored from a checkpoint.
        #
        # Note: broadcast should be done after the first gradient step to ensure optimizer
        # initialization.
        if first_batch:
            hvd.broadcast_variables(mnist_model.variables, root_rank=0)
            hvd.broadcast_variables(opt.variables(), root_rank=0)

        return loss_value


    print('hvd size: %d, rank: %d' %(hvd.size(), hvd.rank()))
    print('Doing training...')

    k = 0
    # Horovod: adjust number of steps based on number of GPUs.
    for batch, (images, labels) in enumerate(dataset.take(1000 // hvd.size())):
        loss_value = training_step(images, labels, batch == 0)

        print('iteration index: %d' % (k))
        k = k + 1
        if batch % 10 == 0 and hvd.local_rank() == 0:
            print('Step #%d\tLoss: %.6f' % (batch, loss_value))

    # Horovod: save checkpoints only on worker 0 to prevent other workers from
    # corrupting it.
    if hvd.rank() == 0:
        print('Doing checkpoint')
        checkpoint.save(checkpoint_dir)
    
    print('Done training.')

if __name__ == '__main__':
    # Set Horovod runtime.
    setHorovodRuntimeEnv()
    main()
    