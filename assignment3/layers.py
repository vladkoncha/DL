from assignment3.im2col import *


def l2_regularization(W, reg_strength):
    """
    Computes L2 regularization loss on weights and its gradient

    Arguments:
      W: np array - weights
      reg_strength: - float value

    Returns:
      loss: single value - l2 regularization loss
      gradient: np.array same shape as W - gradient of weight by l2 loss
    """
    loss = reg_strength * np.sum(np.square(W))
    grad = 2 * reg_strength * W

    return loss, grad


def softmax(predictions):
    """
    Computes probabilities from scores

    Arguments:
      predictions: np array, shape is either (N) or (batch_size, N) -
        classifier output

    Returns:
      probs: np array of the same shape as predictions -
        probability for every class, 0..1
    """
    if predictions.ndim == 1:
        normalized_predictions = predictions - np.max(predictions)
        probs = np.exp(normalized_predictions) / np.sum(np.exp(normalized_predictions))
    else:
        normalized_predictions = predictions - np.max(predictions, axis=1)[:, None]
        probs = np.apply_along_axis(lambda x: np.exp(x) / np.sum(np.exp(x)), 1, normalized_predictions)
    return probs


def cross_entropy_loss(probs, target_index):
    """
    Computes cross-entropy loss

    Arguments:
      probs: np array, shape is either (N) or (batch_size, N) -
        probabilities for every class
      target_index: np array of int, shape is (1) or (batch_size) -
        index of the true class for given sample(s)

    Returns:
      loss: single value
    """
    if probs.ndim == 1:
        loss = -np.log(probs[target_index])
    else:
        target_index_vect = target_index.reshape(-1, 1)
        loss = -np.sum(np.log(np.take_along_axis(probs, target_index_vect, axis=1))) / probs.shape[0]

    return loss


def softmax_with_cross_entropy(predictions, target_index):
    """
    Computes softmax and cross-entropy loss for model predictions,
    including the gradient

    Arguments:
      predictions: np array, shape is either (N) or (batch_size, N) -
        classifier output
      target_index: np array of int, shape is (1) or (batch_size) -
        index of the true class for given sample(s)

    Returns:
      loss, single value - cross-entropy loss
      dprediction, np array same shape as predictions - gradient of predictions by loss value
    """
    y_true = np.zeros(predictions.shape)
    if predictions.ndim == 1:
        y_true[target_index] = 1
    else:
        target_index_vect = target_index.reshape(-1, 1)
        np.put_along_axis(y_true, target_index_vect, 1, axis=1)

    probs = softmax(predictions)
    loss = cross_entropy_loss(probs, target_index)

    dprediction = (probs - y_true)
    if predictions.ndim != 1:
        dprediction /= predictions.shape[0]

    return loss, dprediction


class Param:
    """
    Trainable parameter of the model
    Captures both parameter value and the gradient
    """

    def __init__(self, value):
        self.value = value
        self.grad = np.zeros_like(value)


class ReLULayer:
    def __init__(self):
        self.cache = None

    def forward(self, X):
        # forward pass
        # Hint: you'll need to save some information about X
        # to use it later in the backward pass
        self.cache = X
        return np.maximum(0, X)

    def backward(self, d_out):
        """
        Backward pass

        Arguments:
        d_out, np array (batch_size, num_features) - gradient
           of loss function with respect to output

        Returns:
        d_result: np array (batch_size, num_features) - gradient
          with respect to input
        """
        d_result = np.multiply(d_out, np.int64(self.cache > 0))
        return d_result

    def params(self):
        # ReLU Doesn't have any parameters
        return {}


class FullyConnectedLayer:
    def __init__(self, n_input, n_output):
        self.W = Param(0.001 * np.random.randn(n_input, n_output))
        self.B = Param(0.001 * np.random.randn(1, n_output))
        self.X = None

    def forward(self, X):
        # forward pass
        # Your final implementation shouldn't have any loops
        self.X = X
        return X @ self.W.value + self.B.value

    def backward(self, d_out):
        """
                Backward pass
                Computes gradient with respect to input and
                accumulates gradients within self.W and self.B

                Arguments:
                d_out, np array (batch_size, n_output) - gradient
                   of loss function with respect to output

                Returns:
                d_result: np array (batch_size, n_input) - gradient
                  with respect to input
                """
        # backward pass
        # Compute both gradient with respect to input
        # and gradients with respect to W and B
        # Add gradients of W and B to their `grad` attribute

        # It should be pretty similar to linear classifier from
        # the previous assignment

        self.W.grad += self.X.T @ d_out

        # производная dL/dB = d_out(dL/dZ) * вектор из 1 размерности B
        self.B.grad += np.sum(d_out, axis=0, keepdims=True)

        d_input = d_out @ self.W.value.T
        return d_input

    def params(self):
        return {'W': self.W, 'B': self.B}


class ConvolutionalLayer:
    """https://wiseodd.github.io/techblog/2016/07/16/convnet-conv-layer/"""

    def __init__(self, in_channels, out_channels,
                 filter_size, padding):
        """
        Initializes the layer

        Arguments:
        in_channels, int - number of input channels
        out_channels, int - number of output channels
        filter_size, int - size of the conv filter
        padding, int - number of 'pixels' to pad on each side
        """

        self.filter_size = filter_size
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.W = Param(
            np.random.randn(filter_size, filter_size,
                            in_channels, out_channels)
        )

        self.B = Param(np.zeros(out_channels))
        self.X = None
        self.padding = padding

    def forward(self, X):
        self.X = X.copy()
        batch_size, height, width, channels = X.shape

        X = X.transpose(0, 3, 1, 2)

        stride = 1
        out_height = int((height - self.filter_size + 2 * self.padding) / stride + 1)
        out_width = int((width - self.filter_size + 2 * self.padding) / stride + 1)

        # Implement forward pass
        # Hint: setup variables that hold the result
        # and one x/y location at a time in the loop below

        # It's ok to use loops for going over width and height
        # but try to avoid having any other loops
        X_col = im2col_indices(X, self.filter_size, self.filter_size, padding=self.padding, stride=stride)

        W_col = self.W.value.reshape(self.out_channels, -1)
        out = W_col @ X_col + self.B.value.reshape((-1, 1))

        out = out.reshape(self.out_channels, out_height, out_width, batch_size)
        out = out.transpose(3, 1, 2, 0)

        return out

    def backward(self, d_out):
        # Hint: Forward pass was reduced to matrix multiply
        # You already know how to backprop through that
        # when you implemented FullyConnectedLayer
        # Just do it the same number of times and accumulate gradients

        batch_size, height, width, channels = self.X.shape
        _, out_height, out_width, out_channels = d_out.shape

        stride = 1
        # Implement backward pass
        # Same as forward, setup variables of the right shape that
        # aggregate input gradient and fill them for every location
        # of the output

        X = self.X.transpose(0, 3, 1, 2)
        X_col = im2col_indices(X, self.filter_size, self.filter_size, padding=self.padding, stride=stride)

        db = np.sum(d_out, axis=(0, 1, 2))
        self.B.grad += db

        d_out_reshaped = d_out.transpose(3, 1, 2, 0).reshape(self.out_channels, -1)
        dW = d_out_reshaped @ X_col.T
        dW = dW.reshape(self.W.value.shape)
        self.W.grad += dW

        W_reshaped = self.W.value.reshape(self.out_channels, -1)
        dX_col = W_reshaped.T @ d_out_reshaped
        dX = col2im_indices(dX_col, X.shape,
                            self.filter_size,
                            self.filter_size,
                            padding=self.padding,
                            stride=stride)

        return dX.transpose(0, 2, 3, 1)

    def params(self):
        return {'W': self.W, 'B': self.B}


class MaxPoolingLayer:
    def __init__(self, pool_size, stride):
        """
        Initializes the max pool

        Arguments:
        pool_size, int - area to pool
        stride, int - step size between pooling windows
        """
        self.pool_size = pool_size
        self.stride = stride
        self.X = None

    def forward(self, X):
        self.X = X.copy()
        batch_size, height, width, channels = X.shape
        # Implement maxpool forward pass
        # Hint: Similarly to Conv layer, loop on
        # output x/y dimension

        X = X.transpose(0, 3, 1, 2)

        h_out = (height - self.pool_size) / self.stride + 1
        w_out = (width - self.pool_size) / self.stride + 1

        if not w_out.is_integer() or not h_out.is_integer():
            raise Exception('Invalid output dimension!')

        h_out, w_out = int(h_out), int(w_out)

        X_reshaped = X.reshape(batch_size * channels, 1, height, width)
        X_col = im2col_indices(X_reshaped, self.pool_size, self.pool_size, padding=0, stride=self.stride)

        max_idx = np.argmax(X_col, axis=0)
        out = X_col[max_idx, range(max_idx.size)]

        out = out.reshape(h_out, w_out, batch_size, channels)
        out = out.transpose(2, 0, 1, 3)

        return out

    def backward(self, d_out):
        # Implement maxpool backward pass
        batch_size, height, width, channels = self.X.shape
        X = self.X.transpose(0, 3, 1, 2)

        X_reshaped = X.reshape(batch_size * channels, 1, height, width)
        X_col = im2col_indices(X_reshaped, self.pool_size, self.pool_size, padding=0, stride=self.stride)
        dX_col = np.zeros_like(X_col)

        d_out_flat = d_out.transpose(1, 2, 0, 3).ravel()
        max_idx = np.argmax(X_col, axis=0)
        dX_col[max_idx, range(max_idx.size)] = d_out_flat

        dX = col2im_indices(dX_col,
                            (batch_size * channels, 1, height, width),
                            self.pool_size,
                            self.pool_size,
                            padding=0,
                            stride=self.stride)

        return dX.reshape(X.shape).transpose(0, 2, 3, 1)

    def params(self):
        return {}


class Flattener:
    def __init__(self):
        self.X_shape = None

    def forward(self, X):
        batch_size, height, width, channels = X.shape
        self.X_shape = X.shape

        # Implement forward pass
        # Layer should return array with dimensions
        # [batch_size, hight*width*channels]
        return X.reshape(batch_size, -1)

    def backward(self, d_out):
        # Implement backward pass
        return d_out.reshape(self.X_shape)

    def params(self):
        # No params!
        return {}
