import numpy as np
import numpy.typing as npt


def cosine_similarity(
    vector_a: npt.ArrayLike,
    vector_b: npt.ArrayLike
):
    # like scipy.spatial.distance.cosine
    return np.dot(vector_a, vector_b) / (np.linalg.norm(vector_a) * np.linalg.norm(vector_b))
