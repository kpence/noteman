#!/usr/local/bin/python3
import os
import sys
import getopt
import subprocess
import yaml
import glob
import genanki
import random

def extract_delimited_text(base_str, open_c='{', close_c='}'):
    extracted_texts = []
    num_unclosed_c = 0
    previous_index = 0

    # If invalid arguments (must be 1 character)
    if len(open_c) != 1 or len(close_c) != 1:
        return None
    if open_c == close_c:
        return None

    for ci in range(len(base_str)):
        c = base_str[ci]
        if c == open_c:
            if num_unclosed_c == 0:
                previous_index = ci
            num_unclosed_c += 1
        elif c == close_c:
            if num_unclosed_c == 1:
                extracted_texts.append(base_str[(previous_index+1):ci])
            if num_unclosed_c > 0:
                num_unclosed_c -= 1
    return extracted_texts

def unindent(s):
    indent = len(s)
    for ss in s.split('\n'):
        if ss == '':
            continue
        curr_indent = len(ss) - len(ss.lstrip())
        if curr_indent < indent:
            indent = curr_indent

    res = '\n'.join([ss[indent:] for ss in s.split('\n')])
    return res

class metadata():
    def __init__(self, dct):
        if 'metadata' in dct:
            dct = dct['metadata']
        self.dict = dct
    def __getattr__(self, key):
        if key not in self.dict:
            return 'Unknown'
        return self.dict[key]

class yaml_builder():
    def __init__(self, extractor=extract_delimited_text, delims=['{','}']):
        self.yaml = "\n"
        self.result = None
        self.extractor = extractor
        self.metadata = None
        self.delims = delims
    def add_files(self,files):
        for fn in files.split(' '):
            self.add_file(fn)
        return self
    def add_file(self,fn):
        s = open(fn,'r').read()
        for s in self.extractor(s, open_c=self.delims[0], close_c=self.delims[1]):
            self.yaml += unindent(s) + '\n'
        return self
    def build(self):
        yml = yaml.safe_load(self.yaml)
        if yml is None:
            return self
        if 'metadata' in yml:
            self.metadata = metadata(yml['metadata'])
            del yml['metadata']
        self.result = yml
        return self
    def get_metadata(self):
        return self.metadata
    def get_result(self):
        return self.result

class tasks_command():
    def __init__(self, task_label=''):
        self.tasks = []
        self.task_label = task_label
    def extract_due_date(self, task):
        due_date = ''
        ss = task.split()
        for si in range(len(ss)):
            s = ss[si]
            if s[:4] == "due:":
                due_date = s
                task = ' '.join(ss[:si] + ss[(si+1):])
                break
        return due_date, task
    def add_task(self, project_name, task):
        # Get arguments for commands to be invoked
        project = [f'project:"{self.task_label}::{project_name}"'
                  ,f'project.is:"{self.task_label}::{project_name}"']
        due_date, task = self.extract_due_date(task)
        _desc_base = self.task_label + ':  ' + task
        desc = [_desc_base, f'desc.is:"{_desc_base}"']
        cmd = [ ['task','add',due_date,project[0],desc[0]]
              , ['task','status.not:deleted',project[1],desc[1], 'export'] ]
        
        #print(cmd, task)

        # Check if task has already been created
        resp = subprocess.run(' '.join(cmd[1]), capture_output=True, shell=True, universal_newlines=True)
        already_created = resp.stdout != '[\n]\n'

        if not already_created:
            self.tasks.append(cmd[0])
        else:
            print('Task already created...', task)
            if resp.stderr != '':
                print('ERROR output:', resp.stderr)
        return self
    def add_yaml(self, yml):
        for project_name,project in yml.items():
            if 'tasks' in project:
                for task in project['tasks']:
                    #print(task)
                    self.add_task(project_name, task)
        return self
    def invoke(self):
        if len(self.tasks) > 0:
            print('...Creating Tasks....')
        for task in self.tasks:
            print(task[3])
        for task in self.tasks:
            subprocess.call(task)
        return self

class deck_builder():
    def __init__(self):
        self.deck = None
        self.notes = []
        self.model = genanki.Model(
            1607392319,
            'Simple Model',
            fields=[
                {'name': 'Question'},
                {'name': 'Answer'},
            ],
            templates=[
                {
                    'name': 'Card 1',
                    'qfmt': '{{Question}}',
                    'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
                },
            ])
    def build_deck(self, deck_id=None, deck_name='Unnamed'):
        if deck_id is None:
            deck_id = int(''.join([str(random.randint(0,9)) for _ in range(10)]))
        self.deck = genanki.Deck(deck_id, deck_name)
        for note in self.notes:
            self.deck.add_note(note)
        return (deck_id,deck_name)
    def add_note(self, question, answer):
        note = genanki.Note(model=self.model, fields=[str(question),str(answer)])
        self.notes.append(note)
        return self
    def add_yaml(self, yml):
        for question,answer in yml.items():
            self.add_note(question,answer)
        return self
    def write_to_file(self, fn):
        if len(fn) < 6 or fn[-5:] != '.apkg':
            fn += '.apkg'
        genanki.Package(self.deck).write_to_file(fn)

# Main Script Entry point
if __name__ == '__main__':
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'o:')
    except:
        print('Usage: noteman [-o output file] [file ...]')
        sys.exit(2)

    if len(optlist) == 1:
        file_path = optlist[0][1]
    else:
        file_path = None

    if len(args) == 0:
        input_files = ' '.join(glob.glob('*.md'))
    else:
        input_files = ' '.join(args).strip()

    # Build the flash cards yaml with metadata
    yb = yaml_builder().add_files(input_files).build()
    md = yb.get_metadata()
    assert md is not None, 'No metadata found!'
    yml = yb.get_result()

    # Build tasks yaml
    tasks_yb = yaml_builder(delims=['<','>']).add_files(input_files).build()
    tasks_yml = tasks_yb.get_result()
    if tasks_yml is not None:
        tc = tasks_command(md.label).add_yaml(tasks_yml).invoke()
    else:
        print("No tasks created.")

    # Create the anki deck

    # Check if file_path points to a directory
    if file_path is not None:
        if os.path.isdir(file_path):
            if file_path[-1] != '/':
                file_path += '/'
            file_path += md.filename
    fn = md.filename if file_path is None else file_path
    db = deck_builder().add_yaml(yml)

    # Print the information
    print()
    print(f"Created Deck with {len(db.notes)} Flashcards:")

    deck_id,deck_name = db.build_deck(deck_name=md.deck)
    db.write_to_file(fn)
    print(f"Successfully saved anki deck (id: {deck_id}, name: '{deck_name}') to file '{fn}'")
