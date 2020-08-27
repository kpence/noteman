# noteman

CLI application for generating [Anki](https://ankiweb.net/) flash cards and [Taskwarrior](https://taskwarrior.org/) tasks from Markdown files.

## Installation

```bash
git clone https://github.com/kpence/noteman
cd noteman
pip3 install -r requirements.txt
```

## Usage

```bash
python3 noteman.py *.md
python3 noteman.py file1.md file2.md file3.md directory/*.md
python3 noteman.py -o /path/to/anki-deck-directory *.md
```

## Anki Deck example

To define Anki cards in your markdown file, write the configurations in YAML format enclosed in `{ }` curly brackets.

file1.md:
```
Info Retrieval and Storage
\```metadata
  deck: 'CS::Info Retrieval and Storage'
  filename: 'info-retrieval'
\```
% Note: In the real file, ignore the backslash.

...

Different forms of IR models

\```a
  IR: Information retrieval
  Boolean retrieval model: Simple keyword style of info retrieval based on boolean logic
  Extended boolean retrieval model: 
  Vector space model: 
  Index term: a word or expression which may be stemmed, e.g. a keyword given for a journal article
\```
% Note: In the real file, ignore the backslash.


```

Run the script to generate the Anki deck and save to your file system:
```bash
python3 noteman.py file1.md
```

## Taskwarrior Example (Markdown)

file1.md:
```
Accounting Class
--
%```metadata:
    label: 'accounting'
%```

Week 1 homework:
%```t
Week1:
  notes: Assigned reading
  tasks:
    - 'due:2020-08-24 Read pages 120-150'
%```
% Note: In the real file, ignore the backslash.
```

Then to add the task to your Taskwarrior tasks:
```bash
python3 noteman.py file1.md
```
