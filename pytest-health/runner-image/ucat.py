#!/venv/bin/python
from sys import argv
from upath import UPath
print(UPath(argv[1]).read_text())
