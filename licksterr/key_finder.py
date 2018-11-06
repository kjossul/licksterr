import logging
from collections import deque, defaultdict

from anytree import AnyNode

logger = logging.getLogger(__name__)


class KeyFinder:
    MAJOR_PROFILES = [5.0, 2.0, 3.5, 2.0, 4.5, 4.0, 2.0, 4.5, 2.0, 3.5, 1.5, 4.0]
    MINOR_PROFILES = [5.0, 2.0, 3.5, 4.5, 2.0, 4.0, 2.0, 4.5, 3.5, 2.0, 1.5, 4.0]
    MODULATION_TOLERANCE = 0.3  # % of time a key has to be repeated to be considered a valid modulation

    def __init__(self, penalty=0.8, flat=True):
        self.leaves = self.get_new_gen()
        self.penalty = penalty
        self.flat = flat

    def get_results(self):
        node = max(self.leaves, key=lambda node: node.score)
        keys = []
        while node.parent:
            keys.insert(0, node.key)
            node = node.parent
        # todo analyze modulations
        logger.debug(keys)
        return [max(keys, key=keys.count)]

    def insert_durations(self, durations):
        if not any(durations):
            return
        scores = self.get_segment_score(durations)
        possible_children = defaultdict(list)  # {root: list of possible children for this node}
        next_gen = self.get_new_gen()
        for root in self.leaves:
            for j, score in enumerate(scores):
                penalized_score = root.score + score * (1 if root.key == j else self.penalty)
                if penalized_score > next_gen[j].score:
                    next_gen[j] = KeyNode(key=j, score=penalized_score)
                if penalized_score >= next_gen[j].score:
                    possible_children[root].append(next_gen[j])
        for parent, children in possible_children.items():
            for child in children:
                # The second condition is used to break eventual ties: if the children has another parent, the sum of
                # scores is confronted and the winning parent takes this children
                if child in next_gen and \
                        (not child.parent or child.get_upwards_score() < parent.get_upwards_score() + child.score):
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
    def get_new_gen():
        return [KeyNode(key=key, score=0) for key in range(24)]

    @staticmethod
    def dot(l1, l2):
        if len(l1) != len(l2):
            return 0
        return sum(i[0] * i[1] for i in zip(l1, l2))


class KeyNode(AnyNode):
    def __init__(self, key, score, **kwargs):
        super().__init__(**kwargs)
        self.key = key
        self.score = round(score, 2)

    def __str__(self):
        return f"{self.key} - {self.score}"

    def get_upwards_score(self):
        return self.score + (self.parent.get_upwards_score() if self.parent else 0)
