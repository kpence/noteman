#!/usr/local/bin/python3
import os
import sys
import getopt
import subprocess
import yaml
import glob
import genanki
import random

#ignored_text = ['/br','br/']
ignored_text = []


def extract_delimited_text(base_str, delims=['```open', '```'], apply_to_texts=lambda agg,x,_,__: agg.append(x)):
    open_s = delims[0]
    close_s = delims[1]
    extracted_texts = []
    num_unclosed_c = 0
    previous_index = 0

    # If invalid arguments (must be 1 character)
    if len(open_s) == 0 or len(close_s) == 0:
        return None
    if open_s == close_s:
        return None

    for ci in range(len(base_str)):
        try:
            if base_str[ci:(ci+len(open_s))] == open_s:
                if num_unclosed_c == 0:
                    previous_index = ci
                num_unclosed_c += 1
            elif base_str[ci:(ci+len(close_s))] == close_s:
                if num_unclosed_c == 1:
                    text = base_str[(previous_index+len(open_s)):ci]
                    if text not in ignored_text:
                        if text[-1] != '\n':
                            text += '\n'
                        # A reduce function
                        apply_to_texts(extracted_texts,text, previous_index, ci)
                if num_unclosed_c > 0:
                    num_unclosed_c -= 1
        except IndexError:
            pass
    return extracted_texts


def extract_delimited_text_and_convert_media_links(base_str, delims=['```open','```'], media_path='./'):
    new_media_delims = ['<img src="','">']
    apply_to_texts = get_replace_delimiters_wrapper(new_delims=new_media_delims)
    converted_text = extract_delimited_text(base_str, delims=delims, apply_to_texts=apply_to_texts)
    return converted_text


def get_replace_delimiters_wrapper(original_delims=['![[',']]'], new_delims=['<img src="','">']):
    def apply_to_texts(agg, text, _, __):
        indices = extract_delimited_text(text,
            delims=original_delims,
            apply_to_texts=lambda agg,_,i,j: agg.append((i,j)))

        previous_index = 0
        for start, close in indices:
            agg.append(text[previous_index:start]
                + new_delims[0]
                + text[(start+len(original_delims[0])):close]
                + new_delims[1])
            previous_index = close+len(original_delims[1])
        return agg

    return apply_to_texts


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
        self.dict = dct
    def __getattr__(self, key):
        if key not in self.dict:
            return 'Unknown'
        return self.dict[key]

class yaml_builder():
    def __init__(self, extractor=extract_delimited_text, delims=['```open','```']):
        self.yaml = "\n"
        self.result = None
        self.extractor = extractor
        self.delims = delims
    def add_files(self,files):
        for fn in files:
            self.add_file(fn)
        return self
    def add_file(self,fn):
        try:
            s = open(fn,'r').read()
        except:
            print(sys.exc_info())
            print('Failed to open: ',fn)
            sys.exit(1)
        for s in self.extractor(s, delims=self.delims):
            self.yaml += unindent(s) + '\n'
        return self
    def build(self):
        try:
            yml = yaml.safe_load(self.yaml)
        except:
            print(str(sys.exc_info()))
            print("Failed YAML: {\n",self.yaml, "\n}")
        if yml is None:
            return self
        self.result = yml
        return self
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
        if type(yml) is not dict:
            return self
        for project_name,project in yml.items():
            if 'tasks' in project:
                for task in project['tasks']:
                    print(task)
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
        try:
            for question,answer in yml.items():
                self.add_note(question,answer)
            return self
        except:
            print(sys.exc_info(), yml)
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

    print(sys.argv, "\n\n")
    if len(optlist) == 1:
        file_path = optlist[0][1]
    else:
        file_path = None

    if len(args) == 0:
        input_files = glob.glob('*.md')
    else:
        input_files = args

    # Get the metadat
    md = metadata(yaml_builder(delims=['```metadata','```']).add_files(input_files).build().get_result())
    assert md is not None and md != {}, 'No metadata found!'

    # Build the flash cards yaml with metadata
    yb = yaml_builder(delims=['```a','```'], extractor=extract_delimited_text_and_convert_media_links).add_files(input_files).build()
    yml = yb.get_result()

    # Build tasks yaml
    tasks_yb = yaml_builder(delims=['```t','```']).add_files(input_files).build()
    tasks_yml = tasks_yb.get_result()
    if tasks_yml is not None:
        tc = tasks_command(md.label).add_yaml(tasks_yml).invoke()
    else:
        print("No tasks created.")

    # Create the anki deck

    # Check if file_path points to a directory
    if yml is not None:
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
    else:
        print("No anki deck defined in files.")
