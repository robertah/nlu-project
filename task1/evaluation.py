from config import *
import numpy as np
import tensorflow as tf
import data_utilities
from random import randint
import training_utils as train_utils


def perplexity(sentence, estimate):
    """
    Compute the perplexity of a sentence given its estimate and the word dictionary

    :param sentence: a sentence (in vector form) of test set (sentence_len)
    :param estimate: the estimate of the sentence (sentence_len - 1, vocabulary_size)

    :return: perplexity of the given sentence
    """

    i = 0
    probs = []  # array with word probabilities

    # iterate until we reach the end of the sentence or a pad token
    while i < (sentence_len - 1) and sentence[i] != pad:
        # take the probability related to the true word
        groundtruth_prob = estimate[i][sentence[i]]  # TODO do we start from 1 or 0 in vocabulary?
        probs.append(groundtruth_prob)
        i += 1

    # compute the perplexity
    sentence_perplexity = np.power(2, -1 * (np.log2(probs)).mean())
    print(sentence_perplexity)

    return sentence_perplexity


def write_perplexity(perplexities):
    """
    Write perplexities on file

    :param perplexities: perplexities of test sentences
    """

    output_file = "{}/group{}.perplexity{}".format(output_folder, n_group, experiment)

    with open(output_file, "w") as f:
        for p in perplexities:
            f.write("{}\n".format(p))


def test(test_data):
    """
    Test step: restore the trained model and compute the perplexities for the test data

    :param test_data: dataset used for testing
    """

    print("Testing...")

    # TODO change eval_set into test_set when we have test data

    # Data loading parameters
    tf.flags.DEFINE_string("data_file_path", data_folder, "Path to the data folder.")
    tf.flags.DEFINE_string("test_set", eval_set, "Path to the test data")
    # Test parameters
    tf.flags.DEFINE_integer("batch_size", test_batch_size, "Batch Size (default: 64)")
    tf.flags.DEFINE_string("checkpoint_dir", "./runs/1521480984/checkpoints/", "Checkpoint directory from training run")
    # Tensorflow parameters
    tf.flags.DEFINE_boolean("allow_soft_placement", True, "Allow device soft device placement")
    tf.flags.DEFINE_boolean("log_device_placement", False, "Log placement of ops on devices")

    FLAGS = tf.flags.FLAGS

    print("\nParameters:")
    for attr, value in sorted(FLAGS.__flags.items()):
        print("{}={}".format(attr.upper(), value.value))
    print("")

    print("Loading and preprocessing test dataset \n")

    utils = data_utilities.data_utils(model_to_load, embeddings_size, sentence_len, vocabulary_size, bos,
                                      eos, pad, unk)

    model_w2v, dataset = utils.load_data(eval_set)
    dataset_size = len(dataset)
    print(dataset_size)
    print("Total sentences in the dataset: ", dataset_size)
    print("Example of a random wrapped sentence in dataset ", dataset[(randint(0, dataset_size))])
    print("Example of the first wrapped sentence in dataset ", dataset[0])

    checkpoint_file = tf.train.latest_checkpoint(FLAGS.checkpoint_dir)
    graph = tf.Graph()
    with graph.as_default():
        session_conf = tf.ConfigProto(
            allow_soft_placement=FLAGS.allow_soft_placement,
            log_device_placement=FLAGS.log_device_placement)
        sess = tf.Session(config=session_conf)
        with sess.as_default():
            # Restore the model
            saver = tf.train.import_meta_graph("{}.meta".format(checkpoint_file))
            saver.restore(sess, checkpoint_file)

            # Get placeholders from the graph
            input_x = graph.get_operation_by_name("input_x").outputs[0]
            init_state_hidden = graph.get_operation_by_name("init_state_hidden").outputs[0]
            init_state_current = graph.get_operation_by_name("init_state_current").outputs[0]

            # Evaluation
            prediction = graph.get_operation_by_name("softmax_out_layer/predictions").outputs[0]

            # Create batches for the test data, shuffle not needed
            batches = data_utilities.batch_iter(list(test_data), FLAGS.batch_size, 1, shuffle=False)

            perplexities = []  # array with perplexities for each sentence

            print("Evaluating...")
            for i, batch in enumerate(batches):
                # TODO may need to put words_mapper_to_vocab_indices in data utils since it is used also for testing
                x_batch = train_utils.words_mapper_to_vocab_indices(x_batch, utils.vocabulary_words_list)

                feed_dict = {
                    input_x: batch,
                    init_state_hidden: np.zeros(batch_size, lstm_cell_state),
                    init_state_current: np.zeros(batch_size, lstm_cell_state)
                }
                estimates = sess.run(prediction, feed_dict)

                for j, sentence in enumerate(batch):
                    print("Sentence {} in batch {}".format(j, i))
                    sentence_perplexity = perplexity(sentence, estimates[j])
                    perplexities = np.concatenate([perplexities, sentence_perplexity])

    print("Check if perplexities and test set have the same size: ", len(perplexities) == dataset_size)
    write_perplexity(perplexities)

