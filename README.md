# sparqlcli

SPARQL command-line client based on [rdflib](https://github.com/RDFLib/rdflib) and [SPARQLWrapper](https://github.com/RDFLib/sparqlwrapper).

![image](https://user-images.githubusercontent.com/321111/108711738-1828f600-7516-11eb-95f4-2d093a7976f1.png)

## install

```
python3 -m pip install --user git+https://github.com/FrankGrimm/sparqlcli/
```

Make sure `pip` is installed and `$HOME/.local/bin/` is in your `PATH`.

## usage

`sparqlcli endpoint`

Where `endpoint` is either a remote SPARQL endpoint URI or a local filename.

- `[-f,--format]` one of `html,hturtle,mdata,microdata,n3,nquads,nt,rdfa,rdfa1.0,rdfa1.1,trix,turtle,xml` May be used to avoid format auto-detection when `endpoint` is a local file.
- `[-r,--remote]` Force treating `endpoint` as a remote SPARQL server.
- `[-i,--interactive INTERACTIVE]` Boolean, normally auto-detected if a tty is present.
- `[-o,--output]` output format, one of `table,json,csv`, defaults to table display.
- non-standard prefixes can be registered via `--prefix=longform` as well, e.g. `--foaf=http://xmlns.com/foaf/0.1/`

## examples

Load local file `testdata/demo.nt` with `n-triple` format and pre-register the `foaf` namespace:
```bash
sparqlcli "testdata/demo.nt" "--format=nt" "--foaf=http://xmlns.com/foaf/0.1/"
```

Same as the above with a single query and output type `CSV` (useful for scripting):
```bash
echo "SELECT DISTINCT ?pers WHERE { ?pers rdf:type foaf:Person }" | sparqlcli "testdata/demo.nt" --format=nt "--foaf=http://xmlns.com/foaf/0.1/" --output=csv
```

Query a remote `dbpedia` endpoint:
```bash
sparqlcli "http://dbpedia.org/sparql"
```

Query a remote `dbpedia` endpoint and output data as `json`:

```bash
echo "SELECT DISTINCT ?a ?b WHERE { ?a rdf:type ?b } LIMIT 5" | sparqlcli "http://dbpedia.org/sparql" --output=json
```

## REPL

The REPL features basic auto-complete on standard SPARQL keywords and previous results.

Queries and commands are sent whenever a newline (press Return twice) is encountered or the current input ends with a `;`.

In interactive mode, the following commands are available in addition to simple queries:

- `.edit` open current query buffer in `$EDITOR` (defaults to `vim`)
- `.file <filename>` load and execute query from `<filename>`
- `.watch <filename>` poll `<filename>` for changes and continously execute queries
- `.prefixes`
- up/down arrow keys: navigate through the query history
