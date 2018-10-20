import logging
import os
from collections import defaultdict
from pathlib import Path

from licksterr.guitar import Chord
from licksterr.models import Form, Lick, db, FormLickMatch
from licksterr.queries import get_notes_dict

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.path.realpath(__file__)).parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
ANALYSIS_FOLDER = os.path.join(ASSETS_DIR, "analysis")
FORMS_DB = os.path.join(ANALYSIS_FOLDER, "forms.json")


class Parser:
    def __init__(self):
        self.note_forms_map = get_notes_dict()  # note: {set of forms that contain this note}
        self.all_forms = set(Form.query.all())
        # Mutable objects for analysis
        self.licks_result = defaultdict(float)  # lick: % of time that this lick occupies in the song
        self.notes_result = defaultdict(float)  # note: % of time this note occupies in the song
        self.chords_result = defaultdict(float)  # chord: % of time this chord is played in the song
        # Temporary collections and values for analysis
        self.current_notes = []
        self.form_durations = defaultdict(float)  # form: % of overlapping between form and current lick
        self.lick_duration = 0
        self.measure_counter = 1
        self.track_duration = None

    def parse_song(self, song):
        for guitar_track in song.guitars:
            self.parse_track(guitar_track)

    def parse_track(self, guitar_track):
        """
        Iterates the track beat by beat
        """
        self._init_lick()
        self.track_duration = sum(measure.duration for measure in guitar_track.measures)
        pause_duration = 0
        i = 0
        for i, measure in enumerate(guitar_track.measures, start=1):
            for beat in measure.beats:
                if not beat.notes:
                    pause_duration += beat.duration
                    if pause_duration >= measure.duration:
                        self._add_lick(i)
                    continue
                pause_duration = 0
                notes_length = beat.duration / self.track_duration
                if beat.chord:
                    self._add_lick(i)
                    self.chords_result[Chord(beat.chord)] += notes_length
                else:
                    # Updates duration of objects
                    self.lick_duration += notes_length
                    for note in beat.notes:
                        self.current_notes.append(note)
                        self.notes_result[note] += notes_length
                        for form in self.note_forms_map[note]:
                            self.form_durations[form] += notes_length

        self._add_lick(i)
        db.session.commit()

    def _add_lick(self, current_measure):
        if not self.current_notes:
            return
        lick = Lick(self.current_notes, start=self.measure_counter, end=current_measure, duration=self.lick_duration)
        db.session.add(lick)
        for form, duration in self.form_durations.items():
            score = duration / self.lick_duration
            match = FormLickMatch(form_id=form.id, lick_id=lick.id, score=score)
            db.session.add(match)
        self._init_lick(current_measure)

    def _init_lick(self, current_measure=1):
        self.current_notes.clear()
        self.form_durations = defaultdict(float)
        self.lick_duration = 0
        self.measure_counter = current_measure

    def _init_parser(self):
        self.licks_result.clear()
        self.notes_result.clear()
        self.chords_result.clear()


if __name__ == '__main__':
    pass
