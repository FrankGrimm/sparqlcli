#!/usr/bin/env python
import sys
import os
import rdflib
import rich
import rich.syntax
import rich.traceback
import atexit
import readline
import tempfile
import subprocess

HIST_PATH = "~/.config/sparqlcli/sparqlcli.history"

def fprint(*args, **kwargs):
    rich.print(*args, **kwargs, file=sys.stderr)

def spawn_editor(with_content=""):
    with tempfile.NamedTemporaryFile(suffix=".sparql") as fp:
        fp.write(with_content.encode("utf-8"))
        fp.seek(0)

        editor_cmd = os.environ.get("EDITOR", "vim")
        if editor_cmd is None or editor_cmd == "":
            raise Exception("environment variable EDITOR required")

        editor_process = subprocess.Popen([editor_cmd, fp.name], shell=False)
        editor_process.wait()
        fprint("\[editor returned]", editor_process.returncode)
        if editor_process.returncode != 0:
            return ""

        editor_result = fp.read()
        if editor_result is None:
            editor_result = ""
        else:
            editor_result = editor_result.decode("utf-8")
        return editor_result

HIST_PATH = os.path.expanduser(HIST_PATH)
query = None
is_interactive = sys.stdin.isatty()

if not is_interactive:
    query = " ".join([line.rstrip() for line in sys.stdin]).strip()
    fprint("\[query]", query)

if len(sys.argv) < 2:
    fprint('[red]\[error][/red] missing filename')
    sys.exit(1)

filename = sys.argv[1]
fprint("\[file]", os.path.basename(filename))
prompt = os.path.basename(filename)[:20] + "> "

informat=None
if len(sys.argv) > 2:
    informat = sys.argv[2]
    for format_param in sys.argv[2:]:
        format_param = format_param.lower().strip()
        if not format_param.startswith("--format="):
            continue
        format_param = format_param[len("--format="):]
        informat = format_param
        break
VALID_FORMATS = ["html", "hturtle", "mdata", "microdata", "n3", "nquads", "nt", "rdfa", "rdfa1.0", "rdfa1.1", "trix", "turtle", "xml"]
if informat is not None:
    informat = informat.lower()
    if informat not in VALID_FORMATS:
        fprint(f"[red]\[error][/red] unknown format: {informat}, valid: {','.join(VALID_FORMATS)}")
        sys.exit(1)

g = rdflib.Graph()

for namespace_param in sys.argv[3:]:
    if not namespace_param.startswith("--") or not "=" in namespace_param:
        continue
    namespace_param = namespace_param[2:]
    namespace, longform = namespace_param.split("=", 1)
    namespace = namespace.strip()
    longform = longform.strip()
    g.namespace_manager.bind(namespace, longform)

fprint("\[parsing] format=" + ("auto-detect" if informat is None else informat))
try:
    if informat is None:
        g.parse(filename)
    else:
        g.parse(filename, format=informat)
except Exception as err:
    fprint(f"[red]\[error][/red] {err}")
    sys.exit(1)

fprint("\[parsing complete]")

def exec_query(query):

    lines = query.split("\n")
    query = []
    for line in lines:
        line = line.strip()
        if line.upper().startswith("PREFIX "):
            prefixdata = line.split(" ", 2)
            if len(prefixdata) == 3:
                g.namespace_manager.bind(prefixdata[1], prefixdata[2].strip("<>"), override=True)
                rich.print("\[prefix]", prefixdata[1])
            else:
                rich.print("[red]\[error][/red] syntax: PREFIX prefix <iri>")
        else:
            query.append(line)

    query = "\n".join(query)
    query = query.strip()
    if query == "":
        return

    fprint("\[querying]")
    qres = g.query(query)
    fprint(f"\[query complete] {len(qres)} results")

    table = rich.table.Table()
    for var in qres.vars:
        table.add_column(var.title(), justify="left", no_wrap=False)

    for row in qres:
        rowvals = [val.n3(g.namespace_manager) if val is not None else None for val in row]
        table.add_row(*rowvals)

    rich.print(table)

class SparqlCompleter:
    def __init__(self):
        self.options = ['PREFIX',
                        'SELECT',
                        'WHERE',
                        'DISTINCT',
                        'VALUES']

    def complete(self, text, state):
        response = None
        all_options = self.options + \
                      [f"{ns}:" for ns, _ in g.namespace_manager.namespaces()]

        if state == 0:
            # This is the first time for this text, so build a match list.
            if text:
                self.matches = [s for s in all_options if s and s.lower().startswith(text.lower())]
            else:
                self.matches = all_options[:]

        try:
            response = self.matches[state]
        except IndexError:
            response = None
        return response

def readline_init():
    # readline functionality w/ history
    if not os.path.exists(HIST_PATH):
        os.makedirs(os.path.dirname(HIST_PATH))
    try:
        readline.read_history_file(HIST_PATH)
    except FileNotFoundError:
        with open(HIST_PATH, 'wb') as outfile:
            pass
    readline.set_history_length(1000)
    readline.set_auto_history(False) # manual history management
    readline.set_completer(SparqlCompleter().complete)
    readline.parse_and_bind('tab: complete')
    readline.parse_and_bind('set editing-mode vi')
    atexit.register(readline.write_history_file, HIST_PATH)

def start_interactive_mode():
    fprint("\[interactive mode] starting")
    fprint()

    # nice console output
    rich.pretty.install()
    rich.traceback.install()

    readline_init()

    cancelled = False

    in_query = []
    while not cancelled:
        try:
            line_prompt = prompt if len(in_query) == 0 else "...> "
            rich.print(line_prompt, end='\n' if line_prompt == prompt else '')
            if type(in_query) is not list:
                in_query = []

            in_query.append(input())

            if in_query[-1].strip().lower() in [".exit", ".exit;"]:
                cancelled = True
                continue

            skip_history = False
            if in_query[-1].strip() == "" or ("\n".join(in_query)).strip().endswith(";"):
                in_query = "\n".join(in_query)
                in_query = in_query.strip()

                if in_query.endswith(";"):
                    in_query = in_query.rstrip(";").strip()
                if in_query.endswith(".edit"):
                    in_query = in_query[:-5].strip()
                    in_query = spawn_editor(in_query).strip()
                if in_query.startswith(".file"):
                    readline.add_history(in_query.replace("\n", " "))
                    query_from_file = in_query[len(".file"):].strip()

                    if query_from_file == "":
                        rich.print("[red]\[error][/red] syntax: .file <filename>")
                        in_query = ""
                    elif not os.path.exists(query_from_file):
                        rich.print("[red]\[error][/red] file not found:", query_from_file)
                        in_query = ""
                    else:
                        with open(query_from_file, "rt") as infile:
                            in_query = infile.read().strip()
                            skip_history = True

                if type(in_query) is str and in_query != "":
                    query_output = rich.syntax.Syntax(in_query, "sparql")
                    rich.print()
                    rich.print(query_output)

                    if not skip_history:
                        readline.add_history(in_query.replace("\n", " "))

                    try:
                        exec_query(in_query)
                    except Exception as ex:
                        rich.print(ex)

                in_query = []
                continue
        except EOFError:
            fprint("[exit]")
            cancelled = True
        except KeyboardInterrupt:
            continue
        finally:
            pass

if query is not None:
    exec_query(query)
    sys.exit(0)
else:
    start_interactive_mode()
