import logging
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


class KeyFinder:
    """
    Class for finding the key of a song programmatically.
    Keys go from 0 to 23, the first 12 being Major and the others being minor, both chromatically ordered from C to B.
    It uses a variation of the Krumhansl-Schmuckler key-profile model, which consists in assigning weights to the scale
    degrees (which are different for major and minor scales) and multiplying these profiles with the occurrences of the
    twelve pitch classes in the segment. Flat indicates whether the input values should be adjusted to 0 or 1 (if the
    corresponding pitch class is present or not).
    By segmenting the song we gain the ability to predict modulations: "penalty" is the parameter used to scale the
    scores when the key is changed (it resembles the principle of inertia of a key, meaning that usually songs don't
    jump from one key to another , but tend to stay in a specific key for some time).
    Given n segments of 24 elements each (12+12 keys), the problem consists in finding the list of keys that maximizes
    the scores. Since computing all the 24*n combinations is not feasible, a dynamic-programming approach is used: the
    algorithm stores 24 linked lists, and at every iteration (insert_durations) the node with the highest score for each
    pitch class is kept. In case of ties (two different nodes of the previous generations generated a node with the same
    score for the same pitch class) the parent with the highest score keeps the children. The best match is the linked
    list with the node that has the highest score.
    More info at https://pdfs.semanticscholar.org/2633/fe61583a79ded19348516467971ce3aeb20a.pdf
    """
    MAJOR_PROFILES = (5.0, 2.0, 3.5, 2.0, 4.5, 4.0, 2.0, 4.5, 2.0, 3.5, 1.5, 4.0)
    MINOR_PROFILES = (5.0, 2.0, 3.5, 4.5, 2.0, 4.0, 2.0, 4.5, 3.5, 2.0, 1.5, 4.0)
    MODULATION_TOLERANCE = 0.15  # % of time a key has to be repeated to be considered a valid modulation

    def __init__(self, penalty=0.2, flat=True):
        self.leaves = Node.new_generation()
        self.penalty = penalty
        self.flat = flat

    def get_results(self):
        node = max(self.leaves, key=lambda node: node.score)
        keys = defaultdict(float)
        i = 0
        while node.parent:
            keys[node.key] += 1
            node = node.parent
            i += 1
        return [k for k, v in keys.items() if v / i >= self.MODULATION_TOLERANCE]

    def insert_durations(self, durations):
        if not any(durations):
            return
        scores = self.get_segment_score(durations)
        possible_children = defaultdict(list)  # {root: list of possible children for this node}
        next_gen = Node.new_generation()
        for root in self.leaves:
            for j, score in enumerate(scores):
                penalized_score = root.score + score * (1 if root.key == j else self.penalty)
                if penalized_score > next_gen[j].score:
                    next_gen[j] = Node(key=j, score=penalized_score)
                if penalized_score >= next_gen[j].score:
                    possible_children[root].append(next_gen[j])
        for parent, children in possible_children.items():
            for child in children:
                # If the children has another parent, the parent with the highest score keeps the children
                if child in next_gen and (not child.parent or child.parent.score < parent.score):
                    child.parent = parent
        self.leaves = next_gen

    def get_segment_score(self, durations):
        scores = [0] * 24
        if self.flat:
            durations = [1 if duration else 0 for duration in durations]
        durations = deque(durations)
        for i in range(12):
            scores[i] += self.dot(durations, self.MAJOR_PROFILES)
            scores[i + 12] += self.dot(durations, self.MINOR_PROFILES)
            durations.rotate(-1)
        return scores

    @staticmethod
    def dot(l1, l2):
        if len(l1) != len(l2):
            return 0
        return sum(i[0] * i[1] for i in zip(l1, l2))


class Node:
    def __init__(self, key, score, **kwargs):
        super().__init__(**kwargs)
        self.key = key
        self.score = round(score, 2)
        self.parent = None

    def __str__(self):
        return f"{self.key} - {self.score}"

    def get_upwards_score(self):
        return self.score + (self.parent.get_upwards_score() if self.parent else 0)

    @classmethod
    def new_generation(cls, n=24):
        return [cls(key=key, score=0) for key in range(n)]
