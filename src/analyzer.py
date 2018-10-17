import json
import os
from collections import OrderedDict, defaultdict

from mingus.core import scales, keys

from src import ASSETS_FOLDER
from src.guitar import Form, Lick, Chord, String, Note

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
STRINGS = tuple(String(i, note) for i, note in enumerate('EBGDAE', start=1))


def parse_track(guitar_track):
    start, end = 1, None
    licks = []
    chords = []
    current_notes = []
    for i, measure in enumerate(guitar_track.measures):
        for beat in measure.beats:
            if beat.chord:
                end = i
                licks.append(Lick(current_notes, start, end))
                current_notes.clear()
                start = i
                chords.append(Chord(beat.chord))
            elif beat.notes:
                for note in beat.notes:
                    current_notes.append(note)
            else:  # todo consider a pause after some time (at least one measure?) has passed without notes
                pass
    licks.append(Lick(current_notes, start, i))
    return licks


def build_forms():
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))  # data[key][scale][form] = notes
    for key, scale, form_name in yield_scales(scales_list=SUPPORTED_SCALES):
        form = calculate_form(key, scale, form_name, transpose=True)
        data[key][scale.__name__][form.forms] = [json.loads(note.to_json()) for note in form.notes]
    with open(FORMS_DB, mode='w') as f:
        json.dump(data, f)


def calculate_form(key, scale, form, form_start=0, transpose=False):
    """
    Calculates the notes belonging to this shape. This is done as follows:
    Find the notes on the 6th string belonging to the scale, and pick the first one that is on a fret >= form_start.
    Then progressively build the scale, go to the next string if the distance between the start and the note is
    greater than 3 frets (the pinkie would have to stretch and it's easier to get that note going down a string).
    If by the end not all the roots are included in the form, call the function again and start on an higher fret.
    """
    root_forms = OrderedDict({
        'C': (STRINGS[1], STRINGS[4]),
        'A': (STRINGS[4], STRINGS[2]),
        'G': (STRINGS[2], STRINGS[0], STRINGS[5]),
        'E': (STRINGS[0], STRINGS[5], STRINGS[3]),
        'D': (STRINGS[3], STRINGS[1]),
    })
    notes_list = []
    roots = [next(note for note in root_forms[form][0][key] if note.fret >= form_start)]
    roots.extend(next(note for note in string[key] if note.fret >= roots[0].fret)
                 for string in root_forms[form][1:])
    scale_notes = scale(key).ascending()
    candidates = STRINGS[5].get_notes(scale_notes)
    # picks the first note that is inside the form
    notes_list.append(next(note for note in candidates if note.fret >= form_start))
    start = notes_list[0].fret
    for string in reversed(STRINGS):
        i = string.index
        if i == 1:
            # Removes notes on the low E below the one just found on the high E to keep shape symmetrical
            while notes_list[0].fret < start:
                notes_list.pop(0)
            # checks if the low e is missing a note that we found on the high E
            removed = notes_list.pop()
            if notes_list[0].fret != removed.fret:
                notes_list.insert(0, STRINGS[5].notes[removed.fret])
            # Copies the remaining part of the low E in the high E
            for note in (note for note in notes_list.copy() if note.string == 6):
                notes_list.append(STRINGS[0].notes[note.fret])
            break
        for note in string.get_notes(scale_notes):
            if note.fret <= start:
                continue
            # picks the note on the higher string that is closer to the current position of the index finger
            higher_string_note = min(STRINGS[i - 2].get_notes((note.name,)),
                                     key=lambda note: abs(start - note.fret))
            # A note is too far if the pinkie has to go more than 3 frets away from the index finger
            if note.fret - start > 3:
                notes_list.append(higher_string_note)
                start = higher_string_note.fret
                break
            else:
                notes_list.append(note)
    if not set(roots).issubset(set(notes_list)):
        return calculate_form(key, scale, form, form_start=form_start + 1, transpose=transpose)
    return Form(notes_list, key, scale.__name__, form, transpose=transpose)


def yield_scales(scales_list=tuple(scales._Scale.__subclasses__()), keys_list=None, forms='CAGED'):
    for scale in scales_list:
        current_keys = keys_list
        if not current_keys:
            current_keys = keys.minor_keys if scale.type == 'minor' else keys.major_keys
        for key in current_keys:
            for form in forms:
                yield (key, scale, form)


def get_forms_dict():
    with open(FORMS_DB) as f:
        d = json.loads(f.read())
        for key, scale_dict in d.items():
            for scale, form_dict in scale_dict.items():
                for form in form_dict.keys():
                    notes_list = tuple(Note(*note_data) for note_data in d[key][scale][form])
                    d[key][scale][form] = Form(notes_list, key, scale, form)
    return d


if __name__ == '__main__':
    build_forms()
