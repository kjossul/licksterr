import json
import os
from collections import defaultdict
from itertools import chain, combinations

from mingus.core import scales, keys

from src import ASSETS_FOLDER
from src.guitar import Form, Lick, Chord, Note

ANALYSIS_FOLDER = os.path.join(ASSETS_FOLDER, "analysis")
FORMS_DB = os.path.join(ANALYSIS_FOLDER, "forms.json")
SUPPORTED_SCALES = frozenset((
    scales.Ionian,
    scales.Dorian,
    scales.Phrygian,
    scales.Lydian,
    scales.Mixolydian,
    scales.Aeolian,
    scales.Locrian,
    scales.MinorPentatonic,
    scales.MajorPentatonic,
    scales.MinorBlues,
    scales.MajorBlues
))


class Parser:
    def __init__(self, song):
        self.song = song
        self.forms_db = None   # note_form_dict[note] = {set of forms that contain this note}
        self.note_forms_map = defaultdict(set)
        self.forms_result = defaultdict(list)
        self.all_forms = set()
        self.chords = []
        self.parse_forms_db()

    def parse_song(self, song):
        for guitar_track in song.guitars:
            self.parse_track(guitar_track)

    def parse_track(self, guitar_track):
        start, end = 1, None
        current_notes = []
        possible_forms = self.all_forms.copy()
        for i, measure in enumerate(guitar_track.measures):
            for beat in measure.beats:
                if beat.chord:
                    end = i
                    lick = Lick(current_notes, start, end)
                    self.update_forms_result(lick, possible_forms)
                    # Check performance improvement when information on available forms is kept (i.e. comment this line)
                    possible_forms = self.all_forms.copy()
                    current_notes.clear()
                    start = i
                    self.chords.append(Chord(beat.chord))
                elif beat.notes:
                    for note in beat.notes:
                        possible_forms.intersection_update(self.note_forms_map[note])
                        current_notes.append(note)
                else:  # todo consider a pause after some time (at least one measure?) has passed without notes
                    pass
        lick = Lick(current_notes, start, i)
        self.update_forms_result(lick, possible_forms)

    def update_forms_result(self, lick, possible_forms):
        matching_forms = {form for form in possible_forms if form.contains(lick)}
        for form in matching_forms:
            self.forms_result[form].append(lick)


    def parse_forms_db(self):
        with open(FORMS_DB) as f:
            self.forms_db = json.loads(f.read())
            for key, scale_dict in self.forms_db.items():
                for scale, form_dict in scale_dict.items():
                    for form in form_dict.keys():
                        notes_list = tuple(Note(*note_data) for note_data in self.forms_db[key][scale][form])
                        f = Form(notes_list, key, scale, form)
                        self.forms_db[key][scale][form] = f
                        self.all_forms.add(f)
                        for note in notes_list:
                            self.note_forms_map[note].add(f)


def build_forms():
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))  # data[key][scale][form] = notes
    for key, scale in yield_scales(scales_list=SUPPORTED_SCALES):
        current_forms = {}
        for form_name in 'CAGED':
            current_forms[form_name] = Form.calculate_form(key, scale, form_name, transpose=True)
            data[key][scale.__name__][form_name] = [json.loads(note.to_json())
                                                    for note in current_forms[form_name].notes]
        # Stores also all the possible combinations of each form
        for combo in chain.from_iterable(combinations('CAGED', i) for i in range(2, 6)):
            combo_form = Form.join_forms(current_forms[form] for form in combo)
            data[key][scale.__name__][combo_form.forms] = [json.loads(note.to_json()) for note in combo_form.notes]
    with open(FORMS_DB, mode='w') as f:
        json.dump(data, f)


def yield_scales(scales_list=tuple(scales._Scale.__subclasses__()), keys_list=None):
    for scale in scales_list:
        current_keys = keys_list
        if not current_keys:
            current_keys = keys.minor_keys if scale.type == 'minor' else keys.major_keys
        for key in current_keys:
            yield key, scale




if __name__ == '__main__':
    build_forms()
