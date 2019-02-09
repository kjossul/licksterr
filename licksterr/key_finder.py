import logging
from collections import deque, defaultdict, namedtuple, Counter

from mingus.core import notes

logger = logging.getLogger(__name__)

Profile = namedtuple("Profile", "major minor")


class KeyFinderAggregator:
    """
    A class for aggregating finders with different key-score profiles. The list used can be found at
    http://extras.humdrum.org/man/keycor/
    """
    PROFILES = {
        # Strong tendency to identify the dominant key as the tonic.
        "krumhansl-kessler": Profile((6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88,),
                                     (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)),
        # Weak tendency to identify the subdominant key as the tonic.
        "aarden-essen": Profile((17.7661, 0.145624, 14.9265, 0.160186, 19.8049, 11.3587, 0.291248, 22.062, 0.145624,
                                 8.15494, 0.232998, 4.95122),
                                (18.2648, 0.737619, 14.0499, 16.8599, 0.702494, 14.4362, 0.702494, 18.6161, 4.56621,
                                 1.93186, 7.37619, 1.75623)),
        # No particular tendencies for confusions with neighboring keys.
        "bellman-budge": Profile((16.80, 0.86, 12.95, 1.41, 13.49, 11.93, 1.25, 20.28, 1.80, 8.04, 0.62, 10.57),
                                 (18.16, 0.69, 12.99, 13.34, 1.07, 11.15, 1.38, 21.07, 7.49, 1.53, 0.92, 10.21)),
        # Strong tendency to identify the relative major as the tonic in minor keys. Well-balanced for major keys.
        "temperley-kostka-payne": Profile(
            (0.748, 0.060, 0.488, 0.082, 0.670, 0.460, 0.096, 0.715, 0.104, 0.366, 0.057, 0.400),
            (0.712, 0.084, 0.474, 0.618, 0.049, 0.460, 0.105, 0.747, 0.404, 0.067, 0.133, 0.330)),
        # Performs most consistently with large regions of music, becomes noisier with smaller regions of music.
        "simple": Profile((2, 0, 1, 0, 1, 1, 0, 2, 0, 1, 0, 1),
                          (2, 0, 1, 1, 0, 1, 0, 2, 1, 0, 0.5, 0.5)),
        # https://pdfs.semanticscholar.org/2633/fe61583a79ded19348516467971ce3aeb20a.pdf
        "temperley": Profile((5.0, 2.0, 3.5, 2.0, 4.5, 4.0, 2.0, 4.5, 2.0, 3.5, 1.5, 4.0),
                             (5.0, 2.0, 3.5, 4.5, 2.0, 4.0, 2.0, 4.5, 3.5, 2.0, 1.5, 4.0))
    }

    def __init__(self):
        self.finders = tuple(KeyFinder(major_profiles=profile.major, minor_profiles=profile.minor, name=name)
                             for name, profile in self.PROFILES.items())

    def insert_durations(self, durations):
        for finder in self.finders:
            finder.insert_durations(durations)

    def get_results(self):
        c = Counter(finder.get_results() for finder in self.finders)
        return c.most_common(1)[0][0]


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

    def __init__(self, major_profiles, minor_profiles, name="", penalty=0.2, modulation_tolerance=0.15, flat=True):
        self.leaves = Node.new_generation()
        self.major_profiles = major_profiles
        self.minor_profiles = minor_profiles
        self.name = name
        self.penalty = penalty
        # % of time a key has to be repeated to be considered a valid modulation
        self.modulation_tolerance = modulation_tolerance
        self.flat = flat

    def get_results(self):
        node = max(self.leaves, key=lambda node: node.score)
        keys = defaultdict(float)
        i = 0
        while node.parent:
            keys[node.key] += 1
            node = node.parent
            i += 1
        return tuple(k for k, v in keys.items() if v / i >= self.modulation_tolerance)

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
                if penalized_score >= next_gen[j].score:  # keeps ties
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
            scores[i] += self.dot(durations, self.major_profiles)
            scores[i + 12] += self.dot(durations, self.minor_profiles)
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
        self.score = score
        self.parent = None
        self.name = notes.int_to_note(self.key % 12)
        if self.key >= 12:
            self.name = self.name.lower()

    def __str__(self):
        return f"{self.name} - {self.score}"

    def get_upwards_score(self):
        return self.score + (self.parent.get_upwards_score() if self.parent else 0)

    @classmethod
    def new_generation(cls, n=24):
        return [cls(key=key, score=0) for key in range(n)]
