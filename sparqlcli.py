#!/usr/bin/env python
import sys
import os
import argparse
import atexit
import readline
import tempfile
import subprocess
import json
try:
    from urlparse import urlparse
except:
    from urllib.parse import urlparse

import rdflib
import rich
import rich.syntax
import rich.console
import rich.traceback

HIST_PATH = "~/.config/sparqlcli/sparqlcli.history"

args = None
console = None

def is_url(t):
    try:
        parsed = urlparse(t)
        return all([parsed.scheme, parsed.netloc])
    except:
        return False

def fprint(*pargs, **kwargs):
    if args is None or not args.interactive:
        print(*pargs, **kwargs, file=sys.stderr)
    else:
        rich.print(*pargs, **kwargs, file=sys.stderr)

def vprint(*pargs, **kwargs):
    if args is None or args.verbose:
        fprint(*pargs, **kwargs)

def spawn_editor(with_content=""):
    with tempfile.NamedTemporaryFile(suffix=".sparql") as fp:
        fp.write(with_content.encode("utf-8"))
        fp.seek(0)

        editor_cmd = os.environ.get("EDITOR", "vim")
        if editor_cmd is None or editor_cmd == "":
            raise Exception("environment variable EDITOR required")

        editor_process = subprocess.Popen([editor_cmd, fp.name], shell=False)
        editor_process.wait()
        vprint("\[editor returned]", editor_process.returncode)
        if editor_process.returncode != 0:
            return ""

        editor_result = fp.read()
        if editor_result is None:
            editor_result = ""
        else:
            editor_result = editor_result.decode("utf-8")
        return editor_result

query = None

def parse_args():
    parser = argparse.ArgumentParser(description="sparqlcli client")
    parser.add_argument('endpoint', help='filename or remote SPARQL endpoint')
    parser.add_argument('-r', '--remote',
                        default=None,
                        required=False,
                        action='store_true',
                        help='specify if endpoint is a file or remote (optional, auto-detected if omitted)')

    parser.add_argument('-i', '--interactive',
                        default=None,
                        required=False,
                        type=bool,
                        help='interactive mode (optional, auto-detected)')

    parser.add_argument('-f', '--format',
                        choices=["html", "hturtle", "mdata", "microdata", "n3", "nquads", "nt", "rdfa", "rdfa1.0", "rdfa1.1", "trix", "turtle", "xml"],
                        required=False,
                        default=None,
                        help='input format for local files (auto-detected if not specified)')

    parser.add_argument('-o', '--output',
                        required=False,
                        default='table',
                        choices=['table', 'json', 'csv'],
                        help='output format')

    parser.add_argument("-v", "--verbose", action='store_true', default=False,
                        help="enable verbose output")

    args, prefix_args = parser.parse_known_args()
    if args.remote is None:
        args.remote = is_url(args.endpoint)

    if not args.remote and not os.path.exists(args.endpoint):
        raise argparse.ArgumentTypeError(f"file not found: {args.endpoint}")

    if args.interactive is None:
        args.interactive = sys.stdin.isatty()

    return args, prefix_args

try:
    args, prefix_args = parse_args()
except (argparse.ArgumentError, argparse.ArgumentTypeError) as arg_ex:
    fprint(f"[red]\[error][/red] {arg_ex}")
    sys.exit(1)

if not args.interactive:
    query = " ".join([line.rstrip() for line in sys.stdin]).strip()
    vprint("\[query]", query)

prompt = "> "

def add_namespace_params(g):
    for namespace_param in prefix_args:
        if not namespace_param.startswith("--") or not "=" in namespace_param:
            continue
        namespace_param = namespace_param[2:]
        namespace, longform = namespace_param.split("=", 1)
        namespace = namespace.strip()
        longform = longform.strip()
        g.namespace_manager.bind(namespace, longform)

def load_local(args):
    filename = args.endpoint
    fprint("\[file]", os.path.basename(filename))
    prompt = os.path.basename(filename)[:20] + "> "

    g = rdflib.Graph()
    add_namespace_params(g)

    fprint("\[parsing] format=" + ("auto-detect" if args.format is None else args.format))

    try:
        if args.format is None:
            g.parse(filename)
        else:
            g.parse(filename, format=args.format)
    except Exception as err:
        fprint(f"[red]\[error][/red] {err}")
        sys.exit(1)

    fprint("\[parsing complete]")
    return g, prompt

def init_remote(args):
    prompt = urlparse(args.endpoint).netloc + "> "

    # return g, prompt
    raise Exception("remote endpoint support not implemented yet")

if args.remote is None or args.remote == False:
    g, prompt = load_local(args)
else:
    g, prompt = init_remote(args)

def rdflib_to_string(g, val):
    if val is None:
        return ""
    if type(val) is rdflib.term.Literal:
        return str(val.toPython())
    return val.n3(g.namespace_manager)

def output_result(qres, query):
    completer_options = set()

    if args.output == "json" or args.output=="csv":
        output_data = {'query': query}
        output_data['bindings'] = [var.title() for var in qres.vars]
        output_data['results'] = []
        for row in qres:
            rowvals = [rdflib_to_string(g, val) if val is not None else None for val in row]
            rowdict = {}
            for idx, val in enumerate(rowvals):
                rowdict[output_data['bindings'][idx]] = val
                if val is not None and str(val) != '':
                    completer_options.add(str(val))
            output_data['results'].append(rowdict)

        if args.output == "json":
            print(json.dumps(output_data), file=sys.stdout)
        else:
            print("\t".join([f'"{var}"' for var in output_data['bindings']]), file=sys.stdout)
            for row in output_data['results']:
                print("\t".join([f'"{row[var]}"' for var in output_data['bindings']]), file=sys.stdout)
    else:
        table = rich.table.Table(title=f"{len(qres)} result" + ("s" if len(qres) > 1 else ""))
        for var in qres.vars:
            table.add_column(var.title(), justify="left", no_wrap=False)

        for row in qres:
            rowvals = [rdflib_to_string(g, val) if val is not None else None for val in row]
            for val in rowvals:
                if val is not None and str(val) != '':
                    completer_options.add(str(val))
            table.add_row(*rowvals)

        rich.print(table, file=sys.stdout)

    return list(completer_options)

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
        return []

    fprint("\[querying]")
    qres = g.query(query)
    vprint(f"\[query complete] {len(qres)} results")

    return output_result(qres, query)

class SparqlCompleter:
    def __init__(self):
        self.options = ['PREFIX',
                        'SELECT',
                        'WHERE',
                        'DISTINCT',
                        'COUNT',
                        'VALUES',
                        '.help',
                        '.exit',
                        '.edit']
        self.dynamic_options = ['foo']
        self.max_dynamic_option_count = 10

    def get_options(self):
        return self.options + \
               [f"{ns}:" for ns, _ in g.namespace_manager.namespaces()] + \
               self.dynamic_options

    def add_dynamic_options(self, new_options):
        if new_options is None:
            return

        prev_options = list(set(self.dynamic_options) - set(new_options))
        self.dynamic_options = prev_options + new_options
        self.dynamic_options = self.dynamic_options[-self.max_dynamic_option_count:]

    def complete(self, text, state):
        response = None
        all_options = self.get_options()

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

def readline_history_init():
    hist_filename = os.path.expanduser(HIST_PATH)
    if not os.path.exists(hist_filename):
        os.makedirs(os.path.dirname(hist_filename))
    try:
        readline.read_history_file(hist_filename)
    except FileNotFoundError:
        with open(hist_filename, 'wb') as outfile:
            pass

def readline_init():
    # readline functionality w/ history
    readline_history_init()
    readline.set_history_length(1000)
    readline.set_auto_history(False) # manual history management

    readline.set_completer_delims(readline.get_completer_delims().replace(":", ""))

    completer = SparqlCompleter()
    readline.set_completer(completer.complete)

    readline.parse_and_bind('tab: menu-complete complete')
    readline.parse_and_bind('set editing-mode vi')
    atexit.register(readline.write_history_file, os.path.expanduser(HIST_PATH))

    return completer

def start_interactive_mode():
    global console

    vprint("\[interactive mode] starting")
    vprint()

    # nice console output
    rich.pretty.install()
    rich.traceback.install()

    completer = readline_init()

    cancelled = False

    in_query = []
    while not cancelled:
        try:
            line_prompt = prompt if len(in_query) == 0 else "...> "
            rich.print(line_prompt, end='\n' if line_prompt == prompt else '')
            if type(in_query) is not list:
                in_query = []

            in_query.append(input())

            if in_query[-1].strip().lower() in [".help", ".help;"]:
                fprint("commands: .help, .exit, .edit")
                in_query = []
                continue

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
                        result_completer_options = exec_query(in_query)
                        if result_completer_options is not None and len(result_completer_options) > 0:
                            completer.add_dynamic_options(result_completer_options)
                    except Exception as ex:
                        rich.print(ex)
                        if args.verbose:
                            if console is None:
                                console = rich.console.Console()
                            console.print_exception()


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
